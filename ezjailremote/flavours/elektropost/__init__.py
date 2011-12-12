import sys
from os import path

from fabric.api import sudo, task, put, puts, cd, env, warn
from fabric.contrib.files import upload_template
from OpenSSL import crypto

from ezjailremote.utils import is_ip


@task
def setup(hostname, host_ip=None, pem_file=None):
    """ Sets up a fully functional mail server according to the elektropost
        instructions at http://erdgeist.org/arts/software/elektropost/

        Parameters:

        hostname: FQDN of the mail host, required

        host_ip: IP address of the host, required, if env.host is not an ip address

        pem_file: path to .pem file, will be used for IMAP and webmail, auto-generated,
            if none is  given
    """
    puts("running elektropost setup")
    # upload patches
    from ezjailremote.flavours import elektropost
    local_resource_dir = path.join(path.abspath(path.dirname(elektropost.__file__)))
    remote_patches_dir = "/tmp/ezjailremote.flavours.elektropost/"
    sudo("mkdir -p %s" % remote_patches_dir)
    put(path.join(local_resource_dir, 'patches'), remote_patches_dir, use_sudo=True)
    remote_patches_dir += 'patches'
    # upload ports options
    sudo("mkdir -p /var/db/ports/")
    put(path.join(local_resource_dir, 'server_root/var/db/ports/*'),
        "/var/db/ports/",
        use_sudo=True)

    if host_ip is None and is_ip.match(env['host']):
        host_ip = env['host']
    if host_ip is None:
        warn("No primary IP address specified! Either call using an ip address as "
            "host or explicitly pass one via host_ip")

    # Upload cert
    if pem_file is None:
        pem_file = path.join(local_resource_dir, 'servercert.pem')
        create_self_signed_cert(hostname, pem_file)
    elif not path.exists(pem_file):
        sys.exit("No such .pem '%s'" % pem_file)
    sudo("mkdir -p /var/qmail/control/")
    put(pem_file, "/var/qmail/control/servercert.pem", use_sudo=True)

    # Install qmail
    with cd("/usr/ports/mail/qmail-tls/"):
        sudo("make patch")

    with cd("/var/ports/basejail/usr/ports/mail/qmail-tls/work/qmail-1.03"):
        sudo("patch < %s" % path.join(remote_patches_dir, 'validrcptto.cdb.patch.new'))
        sudo("patch < %s" % path.join(remote_patches_dir, 'qmail-smtpd.c.privacy.patch'))

    with cd("/usr/ports/mail/qmail-tls/"):
        sudo("make install")
    sudo('echo "QMAIL_SLAVEPORT=tls" >> /etc/make.conf')

    # Configure qmail
    sudo("echo %s > /var/qmail/control/me" % hostname)
    sudo('ln -s /var/qmail/boot/qmail-smtpd.rcNG /usr/local/etc/rc.d/qmail-smtpd')
    sudo('ln -s /var/qmail/boot/maildir /usr/local/etc/rc.d/qmail')
    sudo('''echo 'qmailsmtpd_enable="YES"' >> /etc/rc.conf''')
    sudo('''echo 'qmailsmtpd_checkpassword="/usr/local/vpopmail/bin/vchkpw"' >> /etc/rc.conf''')
    sudo('cp %s/tcp.smtp /etc/' % remote_patches_dir)
    sudo('tcprules /etc/tcp.smtp.cdb /etc/tcp.smtp.tmp < /etc/tcp.smtp')

    # Install vpopmail
    with cd("/usr/ports/mail/vpopmail"):
        sudo("make install")
    sudo("chown vpopmail:vchkpw /usr/local/vpopmail")
    sudo("chmod u+s ~vpopmail/bin/vchkpw")
    sudo("pw user mod vpopmail -s /bin/sh")
    # Configure vpopmail
    sudo("echo %s > /usr/local/vpopmail/etc/defaultdomain" % hostname)

    # Install dovecot
    with cd("/usr/ports/mail/dovecot"):
        sudo("make install")
    sudo('''echo 'dovecot_enable="YES"' >> /etc/rc.conf''')

    # Configure dovecot
    upload_template(path.join(local_resource_dir, 'dovecot.conf'),
        '/usr/local/etc/dovecot.conf',
        context=dict(
            hostname=hostname,
            dovecot_ip=host_ip),
        backup=False,
        use_sudo=True)

    # Install lighty
    with cd("/usr/ports/www/lightttpd"):
        sudo("make install")
    sudo('''echo 'lighttpd_enable="YES"' >> /etc/rc.conf''')
    sudo('touch /var/log/lighttpd.error.log')
    sudo('chown www:www /var/log/lighttpd.error.log')
    sudo('touch /var/log/lighttpd.access.log')
    sudo('chown www:www /var/log/lighttpd.access.log')
    sudo('mkdir /var/run/lighttpd/')
    sudo('chown www:www /var/run/lighttpd')

    # Configure lighty
    sudo("mkdir /usr/local/etc/lighttpd/")
    upload_template(path.join(local_resource_dir, 'lighttpd.conf'),
        '/usr/local/etc/lighttpd/lighttpd.conf',
        context=dict(
            hostname=hostname,
            httpd_ip=host_ip),
        backup=False,
        use_sudo=True)
    sudo("mkdir -p /usr/local/www/data")
    put(path.join(local_resource_dir, 'data/*.*'),
        "/usr/local/www/data/", use_sudo=True)
    upload_template(path.join(local_resource_dir, 'data/index.html'),
        '/usr/local/www/data/index.html',
        context=dict(
            hostname=hostname,
            httpd_ip=host_ip),
        backup=False,
        use_sudo=True)

    # Install squirrelmail
    with cd("/usr/ports/mail/squirrelmail"):
        sudo("make install")

    # Configure squirrelmail
    upload_template(path.join(local_resource_dir, 'config.php'),
        '/usr/local/www/squirrelmail/config/config.php',
        context=dict(
            hostname=hostname,
            httpd_ip=host_ip),
        backup=False,
        use_sudo=True)

    # Install qmailadmin / ezmlm-idx
    with cd("/usr/ports/mail/qmailadmin"):
        sudo('make install WITH_SPAM_DETECTION=TRUE SPAM_COMMAND="| /usr/local/bin/spamc -f | /usr/local/bin/maildrop" CGIBINDIR=www/squirrelmail/cgi-bin CGIBINSUBDIR= WEBDATADIR=www/squirrelmail WEBDATASUBDIR=qmailadmin')

    # Install qmailadmin plugin for squirrelmail
    with cd("/usr/ports/mail/squirrelmail-qmailadmin_login-plugin"):
        sudo("make install")

    # Install maildrop
    with cd("/usr/ports/mail/maildrop"):
        sudo("make install")

    # Install the maildrop spam sort magic
    sudo("mv %s /usr/local/etc/maildroprc" % path.join(remote_patches_dir, 'maildroprc'))


def create_self_signed_cert(hostname, pem_file):
    """ based on http://skippylovesmalorie.wordpress.com/2010/02/12/how-to-generate-a-self-signed-certificate-using-pyopenssl/
    """
    # create a key pair
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 1024)

    # create a minimal self-signed cert
    cert = crypto.X509()
    cert.get_subject().CN = hostname
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(pkey)
    cert.sign(pkey, 'sha1')

    open(pem_file, "wt").write(
        crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey) +
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
