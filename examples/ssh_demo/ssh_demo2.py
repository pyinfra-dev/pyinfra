from pyinfra import host
from pyinfra.modules import server

SUDO = True

if host.name == '@vagrant/two':

    key_file = open('/tmp/one_vagrant_id_rsa.pub', 'r')
    key = key_file.read().strip()
    server.user(
        {'Add the vagrant public key from one on to two'},
        'vagrant',
        public_keys=[key],
    )
