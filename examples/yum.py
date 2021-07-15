from pyinfra import host
from pyinfra.facts.server import LinuxDistribution, LinuxName
from pyinfra.operations import yum

SUDO = True

# Note: This "if" below is not really required.
# For instance, if you run this deploy on an
# Ubuntu instance (which does not use yum)
# the yum.packages() will simply be skipped
if host.get_fact(LinuxName) in ['CentOS', 'RedHat']:

    yum.packages(
        name='Install some packages',
        packages=['vim-enhanced', 'vim', 'wget'],
        update=True,
    )

linux_distribution = host.get_fact(LinuxDistribution)
linux_id = linux_distribution['release_meta'].get('ID')

if host.get_fact(LinuxName) == 'CentOS':
    yum.key(
        name='Add the Docker CentOS gpg key',
        src='https://download.docker.com/linux/{}/gpg'.format(linux_id),
    )

yum.rpm(
    name='Ensure an rpm is not installed',
    src='snappy',
    present=False,
)

if host.get_fact(LinuxName) in ['CentOS', 'RedHat']:
    yum.rpm(
        name='Install EPEL rpm to enable EPEL repo',
        src='https://dl.fedoraproject.org/pub/epel/epel-release-latest-'
            '{0}.noarch.rpm'.format(linux_distribution['major']),
    )

    yum.packages(
        name='Install Zabbix and htop',
        packages=['zabbix', 'htop'],
        update=True,
    )
