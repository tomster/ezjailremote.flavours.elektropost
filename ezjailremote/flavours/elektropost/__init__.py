from os import path

from fabric.api import sudo, task, put, puts, cd
from OpenSSL import crypto


@task
def setup(hostname, cert_file=None, key_file=None):
    """ Sets up a fully functional mail server according to the elektropost
        instructions at http://erdgeist.org/arts/software/elektropost/

        hostname: FQDN of the mail host, required
        cert_file, key_file: paths to .pem key and certfiles, will be used for IMAP and webmail
    """
    puts("running elektropost setup")
    from ezjailremote.flavours import elektropost
    local_resource_dir = path.join(path.abspath(path.dirname(elektropost.__file__)), 'resources')
    sudo("mkdir -p /var/db/ports/qmail-tls")
    put(path.join(local_resource_dir, 'qmail-tls-options'),
        '/var/db/ports/qmail-tls/options', use_sudo=True)
    with cd("/usr/ports/mail/qmail-tls/"):
        sudo("make patch")

    remote_resource_dir = "/tmp/ezjailremote.flavours.elektropost"
    sudo("mkdir -p %s" % remote_resource_dir)
    put(path.join(local_resource_dir, 'validrcptto.cdb.patch.new'),
        path.join(remote_resource_dir, 'validrcptto.cdb.patch.new'), use_sudo=True)
    put(path.join(local_resource_dir, 'qmail-smtpd.c.privacy.patch'),
        path.join(remote_resource_dir, 'qmail-smtpd.c.privacy.patch'), use_sudo=True)
    with cd("/var/ports/basejail/usr/ports/mail/qmail-tls/work/qmail-1.03"):
        sudo("patch < %s" % path.join(remote_resource_dir, 'validrcptto.cdb.patch.new'))
        sudo("patch < %s" % path.join(remote_resource_dir, 'qmail-smtpd.c.privacy.patch'))

    with cd("/usr/ports/mail/qmail-tls/"):
        sudo("make install")
    sudo('echo "QMAIL_SLAVEPORT=tls" >> /etc/make.conf')


def create_self_signed_cert(hostname, cert_file, key_file):
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

    open(cert_file, "wt").write(
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    open(key_file, "wt").write(
        crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
