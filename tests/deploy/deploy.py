from pyinfra import host, local, state
from pyinfra.operations import files, server


server.shell(
    name='First main operation',
    commands='echo first_main_op',
)

# Create some conditional branches
if host.name == 'somehost':
    server.shell(
        name='Second main operation',
        commands='echo second_main_op',
    )
elif host.name == 'anotherhost':
    local.include('tasks/a_task.py')

# Include the whole file again, but for all hosts
local.include('tasks/a_task.py')

# Do a loop which will generate duplicate op hashes
for i in range(2):
    server.shell(
        name='Loop-{0} main operation'.format(i),
        commands='echo loop_{0}_main_operation'.format(i),
    )

files.file(
    name='Third main operation',
    src='files/a_file',
    dest='/a_file',
)

with state.preserve_loop_order([1, 2]) as loop_items:
    for item in loop_items():
        server.shell(
            name='Order loop {0}'.format(item),
            commands='echo loop_{0}'.format(item),
        )
        server.shell(
            name='2nd Order loop {0}'.format(item),
            commands='echo loop_{0}'.format(item),
        )

if host.name == 'somehost':
    files.template(
        name='Final limited operation',
        src='templates/a_template.j2',
        dest='/a_template',
        is_template=True,
    )
