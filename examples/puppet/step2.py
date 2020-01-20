from pyinfra import host
from pyinfra.modules import puppet, server

SUDO = True

if host.name == '@vagrant/master':
    server.script_template(
        {'Sign the agent, if needed'},
        'templates/sign_agent.bash.j2',
    )

if host.name == '@vagrant/agent':
    puppet.agent()
