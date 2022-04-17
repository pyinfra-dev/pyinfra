from pyinfra.operations import server

server.shell(
    name="Second task operation",
    commands="echo second_task_operation",
)
