# This deploy intentionally sleeps random intervals between operation calls, and
# different branches for each host. This is to ensure that preparing the operations
# in parallel always gives the same result, with the same set of facts for each host.

from random import randint
from time import sleep

from pyinfra import config, host, inventory
from pyinfra.facts.server import Arch, Os
from pyinfra.operations import python, server

config.SUDO = True

sleep(randint(1, 10) * 0.01)
server.shell(
    name="First main operation",
    commands="echo first_main_op",
)

# Create some conditional branches
if host.name == "somehost":
    sleep(randint(1, 10) * 0.01)
    server.shell(
        name="Second main somehost operation",
        commands="echo second_main_op",
    )
    # Give somehost two facts
    sleep(randint(1, 10) * 0.01)
    host.get_fact(Os)
    host.get_fact(Arch)

    assert config.SUDO is True

elif host.name == "anotherhost":
    config.SUDO = False

    sleep(randint(1, 10) * 0.01)
    server.shell(
        name="Second main anotherhost operation",
        commands="echo second_main_op",
    )

    assert config.SUDO is False

else:  # some other host
    host.get_fact(Os)

    # Load fact from a different host
    somehost = inventory.get_host("somehost")
    somehost.get_fact(Os)

    assert config.SUDO is True


def nested_op():
    sleep(randint(1, 10) * 0.01)
    server.shell(
        name="First nested operation",
        commands="echo first_nested_operation",
    )

    if host.name == "anotherhost":
        sleep(randint(1, 10) * 0.01)
        server.shell(
            name="Second nested anotherhost operation",
            commands="echo first_nested_operation",
        )

    if host.name == "somehost":
        server.shell(
            name="Second nested somehost operation",
            commands="echo first_nested_operation",
        )


python.call(name="Function call operation", function=nested_op)


sleep(randint(1, 10) * 0.01)
server.shell(
    name="Third main operation",
    commands="echo third_main_op",
)
