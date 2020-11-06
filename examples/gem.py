from pyinfra import host
from pyinfra.operations import apt, gem

SUDO = True

if host.fact.linux_name in ['Debian', 'Ubuntu']:

    apt.packages(
        name='Install rubygems',
        packages=['rubygems'],
        update=True,
    )

    gem.packages(
        name='Install rspec',
        packages=['rspec'],
    )
