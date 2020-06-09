from pyinfra.operations import server


server.shell(
    {'First task operation'},
    'echo first_task_operation',
)

server.shell(
    {'Second task operation'},
    'echo second_task_operation',
)
