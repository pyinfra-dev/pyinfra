from pyinfra import host, inventory
from pyinfra.operations import init, puppet, server

SUDO = True
USE_SUDO_LOGIN = True

if host in inventory.get_group('master_servers'):
    server.script_template(
        {'Sign the agent, if needed'},
        'templates/sign_agent.bash.j2',
    )

if host in inventory.get_group('agent_servers'):

    init.systemd(
        {'Temp stop puppet agent so we can ensure a good run'},
        'puppet',
        running=False,
    )

    # Either 'USE_SUDO_LOGIN=True' or 'USE_SU_LOGIN=True' for
    # puppet.agent() as `puppet` is added to the path in
    # the .bash_profile.
    # We also expect a return code of:
    # 0=no changes or 2=changes applied
    puppet.agent(
        {'Run the puppet agent'},
        success_exit_codes=[0, 2],
    )
