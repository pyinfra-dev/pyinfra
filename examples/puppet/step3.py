from pyinfra import host
from pyinfra.modules import files, puppet

SUDO = True

if host.name == '@vagrant/master':
    files.template(
        {'Create a puppet manifest'},
        'templates/environments/production/manifests/httpd.pp.j2',
        '/etc/puppetlabs/code/environments/production/manifests/httpd.pp',
    )

if host.name == '@vagrant/agent':
    puppet.agent()
