from pyinfra import host
from pyinfra.modules import files, puppet

SUDO = True
USE_SUDO_LOGIN = True

if host.name == '@vagrant/master':
    files.template(
        {'Create a puppet manifest'},
        'templates/environments/production/manifests/httpd.pp.j2',
        '/etc/puppetlabs/code/environments/production/manifests/httpd.pp',
    )

if host.name == '@vagrant/agent':
    # Either 'USE_SUDO_LOGIN=True' or 'USE_SU_LOGIN=True' for
    # puppet.agent() as `puppet` is added to the path in
    # the .bash_profile.
    puppet.agent()
