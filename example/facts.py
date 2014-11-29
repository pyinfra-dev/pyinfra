# pyinfra
# File: example/facts.py
# Desc: example deploy script to print all facts

from pyinfra.modules import server

# Get details about a directory
server.directory('/etc')
server.directory('/etc/missing')

# Get details about a file
server.file('/etc/issue')
server.file('/var/log/syslog')

# Get/print all facts (which excludes directories & files, hence above)
print server.all_facts()
