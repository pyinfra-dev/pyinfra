from pyinfra import host
from pyinfra.operations import yum

SUDO = True

# Note: This "if" below is not really required.
# For instance, if you run this deploy on an
# Ubuntu instance (which does not use yum)
# the yum.packages() will simply be skipped
if host.fact.linux_name in ['CentOS', 'RedHat']:

    yum.packages(
        name='Install some packages',
        packages=['vim-enhanced', 'vim', 'wget'],
        update=True,
    )

linux_id = host.fact.linux_distribution['release_meta'].get('ID')
print(linux_id)

if host.fact.linux_name == 'CentOS':
    yum.key(
        name='Add the Docker CentOS gpg key',
        src='https://download.docker.com/linux/{}/gpg'.format(linux_id),
    )

yum.rpm(
    name='Ensure an rpm is not installed',
    packages='snappy',
    present=False,
)

if host.fact.linux_name in ['CentOS', 'RedHat']:
    yum.rpm(
        name='Install EPEL rpm to enable EPEL repo',
        src='https://dl.fedoraproject.org/pub/epel/epel-release-latest-'
        '{{  host.fact.linux_distribution.major }}.noarch.rpm',
    )

    yum.packages(
        name='Install Zabbix and htop',
        packages=['zabbix', 'htop'],
        update=True,
    )
