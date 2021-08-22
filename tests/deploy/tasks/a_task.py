from os import path

from pyinfra import local, state
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

# Import a file *relative* to this one (./another_task.py)
local.include(path.join('.', 'nested', 'empty_task.py'))
local.include(path.join('.', 'another_task.py'))
