from pyinfra import host
from pyinfra.modules import ssh

# Note: Not running as sudo, use the vagrant user.
SUDO = False


if host.name == '@vagrant/one':

    ssh.keyscan(
        {'Set add server two to known_hosts on one'},
        'two.example.com',
    )

    ssh.command(
        {'Create file by running echo from one to two'},
        'two.example.com',
        'echo "one was here" > /tmp/one.txt',
        ssh_user='vagrant',
    )
