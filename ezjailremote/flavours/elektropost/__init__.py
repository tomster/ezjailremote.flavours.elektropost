from os import path

from fabric.api import sudo, task, put, puts, cd


@task
def setup(*args, **kw):
    """ This method is called immediately after starting up the jail.
    Any additional keyword arguments passed to the create command from the command
    line are available here in kw
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
