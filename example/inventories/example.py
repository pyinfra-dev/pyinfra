# pyinfra
# File: example/inventories/test.py
# Desc: basic IP based inventory for testing the example
#       see ./hostnames.py for a more advanced example

# Defines a group - group names must be defined in ALL_CAPS
LINUX = [
    '20.20.20.21',
    '20.20.20.22',
    '20.20.20.23',
    '20.20.20.24'
]

BSD = [
    '20.20.20.25'
]
