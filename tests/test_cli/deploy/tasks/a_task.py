from os import path

from pyinfra import local
from pyinfra.operations import server

server.shell(
    name="First task operation",
    commands="echo first_task_operation",
)

for item in [1, 2]:
    server.shell(
        name=f"Task order loop {item}",
        commands=f"echo loop_{item}",
    )
    server.shell(
        name=f"2nd Task order loop {item}",
        commands=f"echo loop_{item}",
    )

# Import a file *relative* to this one (./empty_task.py)
local.include(path.join(".", "nested", "empty_task.py"))

# Import a file from the CWD (tasks/another_task.py)
local.include(path.join("tasks", "another_task.py"))
