from os import path

from utils import call_file_op

from pyinfra import host, local
from pyinfra.api import deploy
from pyinfra.operations import files, server


@deploy("My nested deploy")
def my_nested_deploy():
    server.shell(
        name="First nested deploy operation",
        commands="echo first nested_deploy_op",
    )


@deploy("My deploy")
def my_deploy():
    server.shell(
        name="First deploy operation",
        commands="echo first_deploy_op",
    )

    my_nested_deploy()

    server.shell(
        name="Second deploy operation",
        commands="echo second_deploy_op",
    )


server.shell(
    name="First main operation",
    commands="echo first_main_op",
)

# Create some conditional branches
if host.name == "somehost":
    server.shell(
        name="Second main operation",
        commands="echo second_main_op",
    )
elif host.name == "anotherhost":
    local.include(path.join("tasks", "a_task.py"))

# Include the whole file again, but for all hosts
local.include(path.join("tasks", "a_task.py"))

# Execute the @deploy function
my_deploy()

# Do a loop which will generate duplicate op hashes
for i in range(2):
    server.shell(
        name="Loop-{0} main operation".format(i),
        commands="echo loop_{0}_main_operation".format(i),
    )

call_file_op()

# Ensure complex nested loops don't generate cycles
for item in host.loop([1, 2]):
    server.shell(
        name=f"Order loop {item}",
        commands=f"echo loop_{item}",
    )
    if host.name == "anotherhost" or (item == 2 and host.name == "somehost"):
        for inner_item in host.loop([1, 2]):
            server.shell(
                name=f"Nested order loop {item}/{inner_item}",
                commands=f"echo loop_{item}/{inner_item}",
            )

if host.name == "somehost":
    files.template(
        name="Final limited operation",
        src="templates/a_template.j2",
        dest="/a_template",
        is_template=True,
    )
