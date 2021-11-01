from pyinfra import config, host, inventory
from pyinfra.operations import files, server

config.SUDO = True


# update the /etc/hosts file
def update_hosts_file(name, ip):
    name = name.replace('@vagrant/', '')
    files.line(
        name='Add hosts to /etc/hosts',
        path='/etc/hosts',
        line=r' {}.example.com '.format(name),
        replace='{} {}.example.com {}'.format(ip, name, name),
    )


# ensure all hosts are added to each /etc/hosts file
inv = inventory.get_group('@vagrant')
for item in inv:
    update_hosts_file(item.name, item.fact.ipv4_addresses['eth0'])

if host.name == '@vagrant/two':
    server.hostname(
        name='Set the hostname for two',
        hostname='two.example.com',
    )

if host.name == '@vagrant/one':

    server.hostname(
        name='Set the hostname for one',
        hostname='one.example.com',
    )

    server.shell(
        name='Generate vagrant ssh key',
        commands=(
            'sudo -u vagrant ssh-keygen -t rsa -C vagrant@example.com '
            '-b 4096 -N "" -q -f /home/vagrant/.ssh/id_rsa'
        ),
    )

    files.get(
        name='Download id_rsa.pub from one',
        src='/home/vagrant/.ssh/id_rsa.pub',
        dest='/tmp/one_vagrant_id_rsa.pub',
    )
