from pyinfra import host, inventory
from pyinfra.operations import files, server

SUDO = True


# update the /etc/hosts file
def update_hosts_file(name, ip):
    name = name.replace('@vagrant/', '')
    files.line(
        {'Add hosts to /etc/hosts'},
        '/etc/hosts',
        r' {}.example.com '.format(name),
        replace='{} {}.example.com {}'.format(ip, name, name),
    )


# ensure all hosts are added to each /etc/hosts file
inv = inventory.get_group('@vagrant')
for item in inv:
    update_hosts_file(item.name, item.fact.ipv4_addresses['eth0'])

if host.name == '@vagrant/two':
    server.hostname(
        {'Set the hostname for two'},
        'two.example.com',
    )

if host.name == '@vagrant/one':

    server.hostname(
        {'Set the hostname for one'},
        'one.example.com',
    )

    server.shell(
        {'Generate vagrant ssh key'},
        'sudo -u vagrant ssh-keygen -t rsa -C vagrant@example.com '
        '-b 4096 -N "" -q -f /home/vagrant/.ssh/id_rsa',
    )

    files.get(
        {'Download id_rsa.pub from one'},
        '/home/vagrant/.ssh/id_rsa.pub',
        '/tmp/one_vagrant_id_rsa.pub',
    )
