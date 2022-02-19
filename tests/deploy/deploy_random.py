# This deploy intentionally sleeps random intervals between operation calls, and
# different branches for each host. This is to ensure that preparing the operations
# in parallel always gives the same result, with the same set of facts for each host.

from random import randint
from time import sleep

from pyinfra import facts, host, inventory
from pyinfra.operations import server


sleep(randint(1, 10) * 0.01)
server.shell(
    name='First main operation',
    commands='echo first_main_op',
)

# Create some conditional branches
if host.name == 'somehost':
    sleep(randint(1, 10) * 0.01)
    server.shell(
        name='Second main somehost operation',
        commands='echo second_main_op',
    )
    # Give somehost two facts
    sleep(randint(1, 10) * 0.01)
    host.get_fact(facts.server.Os)
    host.get_fact(facts.server.Arch)
elif host.name == 'anotherhost':
    sleep(randint(1, 10) * 0.01)
    server.shell(
        name='Second main anotherhost operation',
        commands='echo second_main_op',
    )
else:  # some other host
    host.get_fact(facts.server.Os)

    # Load fact from a different host
    somehost = inventory.get_host('somehost')
    somehost.get_fact(facts.server.Os)

sleep(randint(1, 10) * 0.01)
server.shell(
    name='Third main operation',
    commands='echo third_main_op',
)
