# Getting Started

This guide should help describe the basics of deploying stuff with pyinfra. Start by installing pyinfra with [uv](https://docs.astral.sh/uv/) (see [full install instructions](install.md)):

```sh
uv tool install pyinfra
```

To do something with pyinfra you need two things:

[Inventory](inventory-data.md):
: Hosts, groups and data. Hosts are targets for pyinfra to execute commands or state changes (server via SSH, container via Docker, etc). Hosts can be assigned to groups, and data can then be assigned to both groups and individual hosts.

[Operations](using-operations.md):
: Commands to execute or state to apply to the target hosts in the inventory. These come in two forms: **declarative** states *"ensure the iftop apt package is installed"* and **imperative** commands *"execute the uptime command"*.

    Declarative state operations will not make changes unless required by diff-ing the target state against the state of the operation.

## Ad-hoc commands with pyinfra

You can start pyinfra immediately with some ad-hoc command execution. The CLI always takes arguments in order `INVENTORY` then `OPERATIONS`. You can target a SSH server, Docker container or the local machine for quick testing:

```sh
pyinfra INVENTORY OPERATIONS...

# Execute over SSH
pyinfra my-server.net exec -- echo "hello world"

# Execute over SSH with options
pyinfra localhost --ssh-port 2222 --ssh-user vagrant exec -- echo "hello world"

# Execute within a new docker container
pyinfra @docker/ubuntu:22.04 exec -- echo "hello world"

# Execute on the local machine (MacOS/Linux only - for now)
pyinfra @local exec -- echo "hello world"

# Combine multiple targets as a comma separated list
pyinfra my-server.net,@local,@docker/ubuntu:22.04 exec -- uptime
```

When you run this pyinfra connects (or spins up a container), runs the echo command and prints the output. The [CLI page](cli.md) contains more [examples of ad-hoc commands](cli.md#ad-hoc-command-execution).

!!! note "SSH configuration"
    pyinfra will use your SSH config, keys and any agent available to the current user. In short if you can ``ssh`` into the target it should work out of the box. [The SSH connector](connectors/ssh.md), can also be configured via host data variables.

## State definitions

Operations can be used to define the desired state of target hosts. pyinfra will then determine what, if any, changes need to be made and apply them. This means that when you run these operations for a second time, pyinfra won't need to do do anything because the target is already up to date.

```sh
# Ensure a package is installed on a Centos 8 instance
pyinfra my-server.net dnf.packages vim

# Stop a service on a remote host over SSH
pyinfra my-server.net init.systemd httpd running=False _sudo=True
```

In this case you can re-run the above commands and the second time pyinfra will report no changes need to be made.

!!! note "Note for Docker users"
    When using `@docker/IMAGE` syntax, pyinfra will use a new container each run (meaning there will always be changes). You can use the image from the first run in the second (`@docker/IMAGEID`) to test the state change handling.

## Create a Deploy

A deploy is a collection of inventories and operations defined in Python files. These deploys can be saved and reused (committed to git, etc). Think of a deploy like Ansible's playbook or Chef's cookbook.

To get started create an `inventory.py` (or any other Python filename) containing our hosts to target:

```python
 # Define a group as a list of hosts
 my_hosts = [
    # vagrant instance
    ("ubuntu2204", {
       "ssh_port": 2222,
       "ssh_hostname": "localhost",
       "ssh_user": "vagrant",
       "_sudo": True
    }),
   "my-server.net",
   "@docker/ubuntu:22.04"
 ]
```

Each top-level list (or tuple) in the inventory file defines a **group**, and the variable name becomes the group name — so `my_hosts` above creates a group called `my_hosts` containing those three hosts. You can define any number of groups, and a host that appears in more than one list belongs to all of them. Operations always iterate per host, not per group: every operation runs once for every host across all groups (deduplicated), in parallel. See [Inventory & Data](inventory-data.md) for groups, data and `all.py`.

Now create a `deploy.py` (or any other Python filename) containing our operations to execute:

```python
from pyinfra.operations import apt, server

# Declare end state: the vim package should be installed.
# On every run pyinfra checks the host and only runs apt if vim is missing.
apt.packages(
    name="Ensure the vim apt package is installed",
    packages=["vim"],
    update=True,
)
```

This can now be executed like this:

```sh
pyinfra inventory.py deploy.py
```

!!! note "What's going on here?"
    - CLI arguments are positional, any filenames work `inventory.py` and `deploy.py` is merely convention. For more information see [Using the CLI](cli.md).
    - The target hosts need nothing aside the SSH daemon running. See [Connectors](connectors.md) for other systems pyinfra can execute against.
    - Login occurs from the user running pyinfra, as if you ran `ssh my-server.net` directly
    - Privilege escalation is explicit and passed by operation or group/host data, see [Global Arguments](arguments.md)

Some good next documentation pages:

- [Using Operations](using-operations.md) - the go to reference for writing operation code
- [Inventory & Data](inventory-data.md) - the go to reference for writing inventory code
- [Global Arguments](arguments.md) - arguments available in all operations, privilege escalation, retries, etc
- [Using the CLI](cli.md) - detailed CLI usage
- [Frequently Asked Questions](faq.md)

Or, if you prefer to dive right in and learn from real examples, see [the `pyinfra-examples`](https://github.com/pyinfra-dev/pyinfra-examples) repository. 
