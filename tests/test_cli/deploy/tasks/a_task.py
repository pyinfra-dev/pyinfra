from os import path

from pyinfra import local
from pyinfra.operations import server

server.shell(
    name="First task operation",
    commands="echo first_task_operation",
)

for item in [1, 2]:
    server.shell(
        name="Task order loop {0}".format(item),
        commands="echo loop_{0}".format(item),
    )
    server.shell(
        name="2nd Task order loop {0}".format(item),
        commands="echo loop_{0}".format(item),
    )

# Import a file *relative* to this one (./empty_task.py)
local.include(path.join(".", "nested", "empty_task.py"))

# Import a file from the CWD (tasks/another_task.py)
local.include(path.join("tasks", "another_task.py"))
