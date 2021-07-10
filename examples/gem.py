from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apt, gem

SUDO = True

if host.get_fact(LinuxName) in ['Debian', 'Ubuntu']:

    apt.packages(
        name='Install rubygems',
        packages=['rubygems'],
        update=True,
    )

    gem.packages(
        name='Install rspec',
        packages=['rspec'],
    )
