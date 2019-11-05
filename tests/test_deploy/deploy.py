from pyinfra import host, local, state
from pyinfra.modules import server


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
    local.include('a_task.py')

# Include the whole file again, but for all hosts
local.include('a_task.py')

# Do a loop which will generate duplicate op hashes
for i in range(2):
    server.shell(
        {'Loop-{0} main operation'.format(i)},
        'echo loop_{0}_main_operation'.format(i),
    )

server.shell(
    {'Third main operation'},
    'echo third_main_op',
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
