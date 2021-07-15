from pyinfra import host
from pyinfra.facts.rpm import RpmPackages
from pyinfra.facts.server import LinuxDistribution, LinuxName
from pyinfra.operations import dnf

SUDO = True

# Note: This "if" below is not really required.
# For instance, if you run this deploy on an
# Ubuntu instance (which does not use dnf)
# the dnf.packages() will simply be skipped
if host.get_fact(LinuxName) in ['CentOS', 'RedHat']:

    dnf.packages(
        name='Install some packages',
        packages=['vim-enhanced', 'vim', 'wget'],
        update=True,
    )

linux_distribution = host.get_fact(LinuxDistribution)
linux_id = linux_distribution['release_meta'].get('ID')

if host.get_fact(LinuxName) == 'CentOS':
    dnf.key(
        name='Add the Docker CentOS gpg key',
        src='https://download.docker.com/linux/{}/gpg'.format(linux_id),
    )

dnf.rpm(
    name='Ensure an rpm is not installed',
    src='snappy',
    present=False,
)

if host.get_fact(LinuxName) in ['CentOS', 'RedHat']:

    packages = host.get_fact(RpmPackages)
    epel_installed = False
    for p in packages.keys():
        if p.startswith('epel-release'):
            epel_installed = True

    if not epel_installed:
        dnf.rpm(
            name='Install EPEL rpm to enable EPEL repo',
            src='https://dl.fedoraproject.org/pub/epel/epel-release-latest-'
            '{0}.noarch.rpm'.format(linux_distribution['major']),
        )

    dnf.packages(
        name='Install Zabbix and htop',
        packages=['zabbix', 'htop'],
        update=True,
    )
