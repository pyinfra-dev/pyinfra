from pyinfra.operations import server


server.shell(
    name='First task operation',
    commands='echo first_task_operation',
)

server.shell(
    name='Second task operation',
    commands='echo second_task_operation',
)
