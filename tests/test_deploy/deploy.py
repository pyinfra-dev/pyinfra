from pyinfra import host, local
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
