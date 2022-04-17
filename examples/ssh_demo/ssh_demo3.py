from pyinfra import host
from pyinfra.operations import ssh

# Note: Not running as sudo, use the vagrant user.
SUDO = False


if host.name == "@vagrant/one":

    ssh.keyscan(
        name="Set add server two to known_hosts on one",
        hostname="two.example.com",
    )

    ssh.command(
        name="Create file by running echo from one to two",
        hostname="two.example.com",
        command='echo "one was here" > /tmp/one.txt',
        ssh_user="vagrant",
    )
