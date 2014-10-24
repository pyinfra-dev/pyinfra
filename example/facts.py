# pyinfra
# File: example/facts.py
# Desc: example deploy script to print all facts

from pyinfra.modules import server

# Get all facts
print server.all_facts()

# Get details about a directory
print server.directory('/etc')

# Get details about a file
print server.file('/etc/issue')
