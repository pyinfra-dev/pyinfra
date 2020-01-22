from pyinfra import host, inventory
from pyinfra.modules import files, init, server, yum

SUDO = True


# update the /etc/hosts file
def update_hosts_file(name, ip):
    files.line(
        {'Add hosts to /etc/hosts'},
        '/etc/hosts',
        r' {}.example.com '.format(name),
        replace='{} {}.example.com {}'.format(ip, name, name),
    )


# ensure all hosts are added to each /etc/hosts file
masters = inventory.get_group('master_servers')
for item in masters:
    update_hosts_file('master', item.fact.ipv4_addresses['eth0'])
agents = inventory.get_group('agent_servers')
for item in agents:
    update_hosts_file('agent', item.fact.ipv4_addresses['eth0'])


if host in masters:
    server.hostname(
        {'Set the hostname for the Puppet Master'},
        'master.example.com',
    )

if host in agents:
    server.hostname(
        {'Set the hostname for an agent'},
        'agent.example.com',
    )

if host.fact.linux_name in ['CentOS', 'RedHat']:

    yum.packages(
        {'Install chrony for Network Time Protocol (NTP)'},
        ['chrony'],
    )

    major = host.fact.linux_distribution['major']
    yum.rpm(
        {'Install Puppet Repo'},
        'https://yum.puppet.com/puppet6-release-el-{}.noarch.rpm'
        .format(major),
    )

    files.line(
        {'Ensure SELINUX is disabled'},
        '/etc/sysconfig/selinux',
        r'SELINUX=.*',
        replace='SELINUX=disabled',
    )

    # TODO: should reboot after SELINUX is disabled (how to check/easy way to reboot)
    # TODO: how to determine when reboot is complete
    # TODO: run sestatus

if host in masters:

    install = yum.packages(
        {'Install puppet server'},
        ['puppetserver'],
    )

    config = files.template(
        {'Manage the puppet master configuration'},
        'templates/master_puppet.conf.j2',
        '/etc/puppetlabs/puppet/puppet.conf',
    )

    # TODO: tune always shows as changed
    # I think it should only show as changed if there really was a difference.
    # Might have to add a suffix to the sed -i option, then move file only if
    # there is a diff. Maybe?
    tune = files.line(
        {'Tune the puppet server jvm to only use 1gb'},
        '/etc/sysconfig/puppetserver',
        r'^JAVA_ARGS=.*$',
        replace='JAVA_ARGS=\\"-Xms1g -Xmx1g -Djruby.logger.class=com.puppetlabs.'
        'jruby_utils.jruby.Slf4jLogger\\"',
    )

    if install.changed or config.changed or tune.changed:
        init.systemd(
            {'Restart and enable puppetserver'},
            'puppetserver',
            running=True,
            restarted=True,
            enabled=True,
        )

if host in agents:

    yum.packages(
        {'Install puppet agent'},
        ['puppet-agent'],
    )

    files.template(
        {'Manage the puppet agent configuration'},
        'templates/agent_puppet.conf.j2',
        '/etc/puppetlabs/puppet/puppet.conf',
    )

    init.systemd(
        {'Restart and enable puppet agent'},
        'puppet',
        running=True,
        restarted=True,
        enabled=True,
    )
