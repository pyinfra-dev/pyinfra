from pyinfra import config, host, inventory
from pyinfra.operations import files, puppet

config.SUDO = True
config.USE_SUDO_LOGIN = True

if host in inventory.get_group("master_servers"):
    files.template(
        name="Create a puppet manifest",
        src="templates/environments/production/manifests/httpd.pp.j2",
        dest="/etc/puppetlabs/code/environments/production/manifests/httpd.pp",
    )

if host in inventory.get_group("agent_servers"):
    # Either 'USE_SUDO_LOGIN=True' or 'USE_SU_LOGIN=True' for
    # puppet.agent() as `puppet` is added to the path in
    # the .bash_profile.
    # We also expect a return code of:
    # 0=no changes or 2=changes applied
    puppet.agent(
        name="Run the puppet agent",
        success_exit_codes=[0, 2],
    )
