# pyinfra
# File: example/inventories/dev.py
# Desc: hostname based inventory (requires ./hosts in /etc/hosts)

# Defines a group
bsd = [
    'openbsd58.pyinfra',
]

yum = [
    'centos6.pyinfra',
    'centos7.pyinfra',
    'fedora23.pyinfra'
]

apt = [
    # Host-specific data can be attached in inventory
    ('ubuntu14-hosttest', {'ssh_hostname': 'ubuntu14.pyinfra'}),
    'ubuntu15.pyinfra',
    'debian7.pyinfra',
    'debian8.pyinfra'
]

# Hosts can be in multiple groups
linux = yum + apt

# The all group is automatically set to the unique hosts above and so does not need to be defined
# all = linux + bsd
