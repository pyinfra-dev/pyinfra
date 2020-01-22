from pyinfra import host, local

if 'misc_servers' in host.groups:
    local.include('apt.py')
    local.include('npm.py')
    local.include('files.py')
    local.include('server.py')
    local.include('virtualbox/virtualbox.py')

if 'docker_servers' in host.groups:
    local.include('docker_ce.py')
