from pyinfra.api import deploy
from pyinfra.modules import server


@deploy
def do_deploy(state, host):
    server.shell(
        state, host,
        {'Deploy op'},
        'echo first_deploy_operation',
    )


server.shell(
    {'First task operation'},
    'echo first_task_operation',
)

server.shell(
    {'Second task operation'},
    'echo second_task_operation',
)

do_deploy()
