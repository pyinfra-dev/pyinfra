from pyinfra import host
from pyinfra.modules import apt, gem

SUDO = True

if host.fact.linux_name in ['Debian', 'Ubuntu']:

    apt.packages(
        {'Install rubygems'},
        'rubygems',
    )

    gem.packages(
        {'Install rspec'},
        'rspec',
    )
