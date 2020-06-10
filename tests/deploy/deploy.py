from pyinfra import host, local, state
from pyinfra.operations import files, server


server.shell(
    {'First main operation'},
    'echo first_main_op',
)

# Create some conditional branches
if host.name == 'somehost':
    server.shell(
        {'Second main operation'},
        'echo second_main_op',
    )
elif host.name == 'anotherhost':
    local.include('tasks/a_task.py')

# Include the whole file again, but for all hosts
local.include('tasks/a_task.py')

# Do a loop which will generate duplicate op hashes
for i in range(2):
    server.shell(
        {'Loop-{0} main operation'.format(i)},
        'echo loop_{0}_main_operation'.format(i),
    )

files.file(
    {'Third main operation'},
    'files/a_file',
    '/a_file',
)

with state.preserve_loop_order([1, 2]) as loop_items:
    for item in loop_items():
        server.shell(
            {'Order loop {0}'.format(item)},
            'echo loop_{0}'.format(item),
        )
        server.shell(
            {'2nd Order loop {0}'.format(item)},
            'echo loop_{0}'.format(item),
        )

if host.name == 'somehost':
    files.template(
        {'Final limited operation'},
        'templates/a_template.j2',
        '/a_template',
        is_template=True,
    )
