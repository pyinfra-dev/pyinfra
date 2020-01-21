from pyinfra import host
from pyinfra.modules import puppet, server

SUDO = True
USE_SUDO_LOGIN = True

if host.name == '@vagrant/master':
    server.script_template(
        {'Sign the agent, if needed'},
        'templates/sign_agent.bash.j2',
    )

if host.name == '@vagrant/agent':
    # Either 'USE_SUDO_LOGIN=True' or 'USE_SU_LOGIN=True' for
    # puppet.agent() as `puppet` is added to the path in
    # the .bash_profile.
    puppet.agent()
