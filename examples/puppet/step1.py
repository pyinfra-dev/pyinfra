from pyinfra import host, inventory
from pyinfra.facts.hardware import Ipv4Addresses
from pyinfra.facts.server import LinuxDistribution, LinuxName
from pyinfra.operations import files, init, server, yum

SUDO = True


# update the /etc/hosts file
def update_hosts_file(name, ip):
    files.line(
        name='Add hosts to /etc/hosts',
        path='/etc/hosts',
        line=r' {}.example.com '.format(name),
        replace='{} {}.example.com {}'.format(ip, name, name),
    )


# ensure all hosts are added to each /etc/hosts file
masters = inventory.get_group('master_servers')
for group_host in masters:
    update_hosts_file('master', group_host.get_fact(Ipv4Addresses)['eth0'])

agents = inventory.get_group('agent_servers')
for group_host in agents:
    update_hosts_file('agent', group_host.get_fact(Ipv4Addresses)['eth0'])


if host in masters:
    server.hostname(
        name='Set the hostname for the Puppet Master',
        hostname='master.example.com',
    )

if host in agents:
    server.hostname(
        name='Set the hostname for an agent',
        hostname='agent.example.com',
    )

if host.get_fact(LinuxName) in ['CentOS', 'RedHat']:

    yum.packages(
        name='Install chrony for Network Time Protocol (NTP)',
        packages=['chrony'],
    )

    major = host.get_fact(LinuxDistribution)['major']
    yum.rpm(
        name='Install Puppet Repo',
        src='https://yum.puppet.com/puppet6-release-el-{}.noarch.rpm'
        .format(major),
    )

    files.line(
        name='Ensure SELINUX is disabled',
        path='/etc/sysconfig/selinux',
        line=r'SELINUX=.*',
        replace='SELINUX=disabled',
    )

    # TODO: should reboot after SELINUX is disabled (how to check/easy way to reboot)
    # TODO: how to determine when reboot is complete
    # TODO: run sestatus

if host in masters:

    install = yum.packages(
        name='Install puppet server',
        packages=['puppetserver'],
    )

    config = files.template(
        name='Manage the puppet master configuration',
        src='templates/master_puppet.conf.j2',
        dest='/etc/puppetlabs/puppet/puppet.conf',
    )

    # TODO: tune always shows as changed
    # I think it should only show as changed if there really was a difference.
    # Might have to add a suffix to the sed -i option, then move file only if
    # there is a diff. Maybe?
    tune = files.line(
        name='Tune the puppet server jvm to only use 1gb',
        path='/etc/sysconfig/puppetserver',
        line=r'^JAVA_ARGS=.*$',
        replace='JAVA_ARGS=\\"-Xms1g -Xmx1g -Djruby.logger.class=com.puppetlabs.'
        'jruby_utils.jruby.Slf4jLogger\\"',
    )

    if install.changed or config.changed or tune.changed:
        init.systemd(
            name='Restart and enable puppetserver',
            service='puppetserver',
            running=True,
            restarted=True,
            enabled=True,
        )

if host in agents:

    yum.packages(
        name='Install puppet agent',
        packages=['puppet-agent'],
    )

    files.template(
        name='Manage the puppet agent configuration',
        src='templates/agent_puppet.conf.j2',
        dest='/etc/puppetlabs/puppet/puppet.conf',
    )

    init.systemd(
        name='Restart and enable puppet agent',
        service='puppet',
        running=True,
        restarted=True,
        enabled=True,
    )
