from pyinfra import config, host
from pyinfra.operations import server

config.SUDO = True

if host.name == "@vagrant/two":

    key_file = open("/tmp/one_vagrant_id_rsa.pub", "r")
    key = key_file.read().strip()
    server.user(
        name="Add the vagrant public key from one on to two",
        user="vagrant",
        public_keys=[key],
    )
