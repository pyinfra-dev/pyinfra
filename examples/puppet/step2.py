from pyinfra import host, inventory
from pyinfra.modules import puppet, server

SUDO = True
USE_SUDO_LOGIN = True

if host in inventory.get_group('master_servers'):
    server.script_template(
        {'Sign the agent, if needed'},
        'templates/sign_agent.bash.j2',
    )

if host in inventory.get_group('agent_servers'):
    # Either 'USE_SUDO_LOGIN=True' or 'USE_SU_LOGIN=True' for
    # puppet.agent() as `puppet` is added to the path in
    # the .bash_profile.
    puppet.agent()
