# pyinfra
# File: example/inventories/dev.py
# Desc: hostname based inventory (requires ./hosts in /etc/hosts)

# Defines a group - group names must be defined in ALL_CAPS
BSD = [
    'openbsd58.pyinfra'
]

YUM = [
    'centos6.pyinfra',
    'centos7.pyinfra',
    'fedora23.pyinfra'
]

APT = [
    # Host-specific data can be attached in inventory
    ('ubuntu14-hosttest', {'ssh_hostname': 'ubuntu14.pyinfra'}),
    'ubuntu15.pyinfra',
    'debian7.pyinfra',
    'debian8.pyinfra'
]

# Hosts can be in multiple groups
LINUX = YUM + APT

# ALL is automatically set to the unique hosts above and so does not need to be defined
# ALL = LINUX + BSD
