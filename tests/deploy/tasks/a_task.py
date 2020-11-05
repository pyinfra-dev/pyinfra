from pyinfra import state
from pyinfra.operations import server


server.shell(
    name='First task operation',
    commands='echo first_task_operation',
)

with state.preserve_loop_order([1, 2]) as loop_items:
    for item in loop_items():
        server.shell(
            name='Task order loop {0}'.format(item),
            commands='echo loop_{0}'.format(item),
        )
        server.shell(
            name='2nd Task order loop {0}'.format(item),
            commands='echo loop_{0}'.format(item),
        )

server.shell(
    name='Second task operation',
    commands='echo second_task_operation',
)
