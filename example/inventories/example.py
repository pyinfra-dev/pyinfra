# pyinfra
# File: example/inventories/test.py
# Desc: basic IP based inventory for testing the example
#       see ./hostnames.py for a more advanced example

# Defines a group - group names must be defined in ALL_CAPS
LINUX = [
    # Ubuntu 14
    '20.20.20.21',
    # Ubuntu 15
    '20.20.20.26',
    # CentOS 6
    '20.20.20.22',
    # CentOS 7
    '20.20.20.23',
    # Debian 7
    '20.20.20.24',
    # Debian 8
    '20.20.20.27',
    # Fedora 23
    '20.20.20.28',
    # Gentoo
    '20.20.20.29'
]

BSD = [
    # OpenBSD 5.7
    '20.20.20.25'
]
