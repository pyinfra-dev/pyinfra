from pyinfra import host
from pyinfra.modules import files, server

SUDO = True

if host.name == '@vagrant/two':

    # TODO: Is there a better way?
    files.put(
        {'Upload id_rsa.pub to two in file tmp_authorized_key'},
        '/tmp/one_vagrant_id_rsa.pub',
        '/home/vagrant/.ssh/tmp_authorized_key',
    )

    server.script_template(
        {'Append vagrant@one id_rsa.pub to two authorized_keys'},
        'templates/append_vagrant_key.bash.j2',
    )

    files.directory(
        {'Fix perms on /home/vagrant/.ssh'},
        '/home/vagrant/.ssh',
        mode='700',
        user='vagrant',
        group='root',
    )

    files.file(
        {'Fix perms on authorized_keys file'},
        '/home/vagrant/.ssh/authorized_keys',
        mode='600',
        user='vagrant',
        group='vagrant',
    )
