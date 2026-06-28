# Using Operations

!!! tip "What are operations?"
    Operations come in two flavours:

    - **Declarative** — the common case. You describe an end state (*"the nginx package should be installed"*, *"this file should have these contents"*) and pyinfra checks the host first and only runs commands if reality doesn't match. Re-running a deploy is a no-op when nothing has drifted. Examples: `apt.packages`, `files.file`, `server.user`.
    - **Imperative** — you tell pyinfra to run a specific command unconditionally. These always execute. Examples: `server.shell`, `server.script`, `python.call`.

    Most pyinfra deploys are written in the declarative style; imperative operations are an escape hatch for one-off commands or things no built-in operation covers yet.

For example, these two operations will ensure that user `pyinfra` exists with home directory `/home/pyinfra`, and that the `/var/log/pyinfra.log` file exists and is owned by that user:

```python
from pyinfra.operations import server, files

server.user(
    name="Create pyinfra user",
    user="pyinfra",
    home="/home/pyinfra",
)

files.file(
    name="Create pyinfra log file",
    path="/var/log/pyinfra.log",
    user="pyinfra",
    group="pyinfra",
    mode="644",
)
```

Uses [`operations.files`](operations/files.md) and [`operations.server`](operations/server.md). You can see all available operations in the [Operations Index](operations/index.md). If you save the file as `deploy.py` you can test it out using Docker:

```sh
pyinfra @docker/ubuntu:20.04 deploy.py
```

!!! note "About the `name` argument"
    `name` is a human-readable label used in CLI output and to identify the operation in the execution order — it has no effect on what gets run. The imperative phrasing in the examples (*"Create pyinfra user"*) is purely descriptive: for a declarative operation, pyinfra still checks current state first and only acts if the host differs from the target. If you omit `name`, pyinfra generates one from the operation's call signature.

### From Python to shell

Every operation ultimately compiles down to one or more shell commands (and/or file uploads) executed on the target host. A few flags let you inspect what pyinfra intends to do without mutating anything:

```sh
pyinfra @docker/ubuntu:20.04 deploy.py --debug-operations  # print operation order + metadata, then exit
pyinfra inventory.py deploy.py --dry                        # connect, gather facts, report changes, skip mutations
pyinfra inventory.py deploy.py -vv                          # echo each shell command as it actually runs
```

`--debug-operations` and `--dry` report *which* operations would change *which* hosts — they don't print the literal commands, because those aren't generated until execute time. To see the actual shell, run with `-vv`, which echoes each command as it is sent.

For the `server.user` example above, on a host that doesn't yet have the user, the operation generates something like:

```sh
useradd -d /home/pyinfra -m pyinfra
```

…and nothing at all on a re-run, because the [`server.Users`](facts/server.md#server-Users) fact reports the user already exists. The same pattern applies to every declarative operation: read fact → diff against target → emit only the commands needed to converge.

### When "executing an operation" actually happens

A deploy runs in two phases. First a **prepare** phase: pyinfra runs your Python deploy code once per host, calls the relevant facts on each target to read current state, and uses the result to work out the order operations run in and whether each one will change the host. It does *not* build a stored list of commands here — it only advances each operation far enough to know whether it would change anything. No mutating commands run during prepare. Then an **execute** phase: pyinfra walks the operations in order and, for each one, re-evaluates the operation against every host — re-running its logic to generate the commands, then running them on every host in parallel before moving on to the next operation.

A consequence worth knowing: **deploy code runs before any changes are made on the targets.** If your Python branches on a fact like `host.get_fact(File, "/etc/nginx/conf")` or on `another_op.changed`, that branch is evaluated *during prepare* using the host's state *before any operation in this deploy has run*. For conditions that need to reflect the effect of an earlier operation, use the `_if` argument instead (see [Change Detection](#change-detection) below) — `_if` is evaluated at execute time. The [Deploy Process](deploy-process.md) page walks through this with worked examples.

## Global Arguments

Global arguments are covered in detail here: [Global Arguments](arguments.md). There is a set of arguments available to all operations to control authentication (`_sudo`, etc) and operation execution (`_shell_executable`, etc):

```python
from pyinfra.operations import apt

apt.update(
    name="Update apt repositories",
    _sudo=True,
    _sudo_user="pyinfra",
)
```

Command operations, including `server.shell`, run through the configured shell.
The default shell is `sh`, so raw shell commands should either use POSIX `sh`
syntax or choose a shell explicitly with `_shell_executable`:

```python
from pyinfra.operations import server

server.shell(
    name="Run a Bash login shell command",
    commands=["my-command"],
    _shell_executable="bash -l",
)
```

## The `host` Object

pyinfra provides a global `host` object that can be used to retrieve information and metadata about the current host target. At all times the `host` variable represents the current host context, so you can think about the deploy code executing on individual hosts at a time.

The `host` object has `name` and `groups` attributes which can be used to control operation flow:

```python
from pyinfra import host

if host.name == "control-plane-1":
    ...

if "control-plane" in host.groups:
    ...
```

### Host & Group Data

Adding data to inventories is covered in detail here: [Inventory & Data](inventory-data.md). Data can be accessed within operations using the `host.data` attribute:

```python
from pyinfra import host
from pyinfra.operations import server

# Ensure the state of a user based on host/group data
server.user(
    name="Setup the app user",
    user=host.data.app_user,
    home=host.data.app_dir,
)
```

### Host Facts

Facts allow you to use information about the target host to control and configure operations. A good example is switching between `apt` & `yum` depending on the Linux distribution. You can get a fact like this:

```sh
pyinfra inventory.py fact server.LinuxName
```

Facts are imported from `pyinfra.facts.*` and can be retrieved using the `host.get_fact` function. If you save this in a file called `nano.py`:

```python
from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import yum, apt

if host.get_fact(LinuxName) == "Fedora":
    yum.packages(
        name="Install nano via yum",
        packages=["nano"],
        _sudo=True
    )
if host.get_fact(LinuxName) == "Ubuntu":
    apt.packages(
        name="Install nano via apt",
        packages=["nano"],
        update=True,
        _sudo=True
    )
```

```sh
pyinfra inventory.py nano.py
```

See [Facts Index](facts/index.md) for a full list of available facts and arguments.

!!! important
    Only use **immutable** facts in deploy code — facts whose value cannot change *over the course of the deploy*. OS family, distribution, architecture and kernel version are immutable in this sense; "is this package installed", "does this file exist" and "is this service running" are **not**, because an earlier operation in the same deploy could flip them. Facts are read during prepare, before any operation runs, so a mutable fact branched on in Python sees pre-deploy state — not the state at the point of the branch in source order. Use `_if` (see [Change Detection](#change-detection) below) for conditions that need execute-time evaluation. More detail: [using host facts](deploy-process.md#using-host-facts).

#### Fact Errors

When a fact command exits with a non-zero status the host is marked as failed, just as when an operation fails. This can be avoided by passing the `_ignore_errors` argument:

```python
if host.get_fact(LinuxName, _ignore_errors=True):
    ...
```

!!! important
    Facts may choose to silently ignore errors for missing commands (eg mysql not installed) and instead return a default value. In v4 this will raise an error during the execution phase.

## The `inventory` Object

Like `host`, there is an `inventory` object that can be used to access the entire inventory of hosts. This is useful when you need facts or data from another host like the hostname of another server:

```python
from pyinfra import inventory
from pyinfra.facts.server import Hostname
from pyinfra.operations import files

# Get the other host, load the hostname fact
db_host = inventory.get_host("postgres-main")
db_hostname = db_host.get_fact(Hostname)

files.template(
    name="Generate app config",
    src="templates/app-config.j2.yaml",
    dest="/opt/myapp/config.yaml",
    db_hostname=db_hostname,
)
```

## Change Detection

Every operation call returns an `OperationMeta` object — a handle representing the work pyinfra has scheduled for that operation against the current host. During the **prepare** phase you only know whether the operation *would* change anything (`will_change`); after the **execute** phase the handle also exposes the actual result, output and whether it succeeded.

The most common use is to gate a later operation on whether an earlier one ran or succeeded. Because deploy code runs in prepare, you cannot do this with a plain `if`; pass a callable to the `_if` global argument and pyinfra will evaluate it at execute time. The meta object exposes four such gating helpers:

- `did_change` — true if the operation actually executed at least one command on this host
- `did_not_change` — the inverse
- `did_succeed` — true if the operation finished without error (covers both "ran and succeeded" and "no change needed")
- `did_error` — true if any of the operation's commands failed

For output (`stdout`, `stderr`, `stdout_lines`, `stderr_lines`) see [Output & Callbacks](#output-callbacks) below — these are only readable after execution, so they need a callback rather than direct access in deploy code.

```python
from pyinfra.operations import server

create_user = server.user(...)
create_otheruser = server.user(...)

server.shell(
    name="Bootstrap myuser",
    commands=["..."],
    # Only execute this operation if the first user create executed any changes
    _if=create_user.did_change,
)

# A list can be provided to run an operation if **all** functions return true
server.shell(
    commands=["echo 'Both myuser and otheruser changed'"],
    _if=[create_user.did_change, create_otheruser.did_change],
)

# You can also build your own lamba functions to achieve, e.g. an OR condition
server.shell(
    commands=["echo 'myuser or otheruser changed'"],
    _if=lambda: create_user.did_change() or create_otheruser.did_change(),
)

# The functions `any_changed` and `all_changed` are provided for common use cases, e.g.
from pyinfra.operations.util import any_changed, all_changed
server.shell(commands=["..."], _if=any_changed(create_user, create_otheruser))
server.shell(commands=["..."], _if=all_changed(create_user, create_otheruser))
```

!!! important
    `_if` must be a callable, or a list of callables. Passing a value directly (e.g. `_if=host.get_fact(MyFact)`) does not gate the operation: most non-callable values raise `ArgumentTypeError` at prepare time, and `None` is treated as "no condition" so the operation always runs. Wrap the value in a lambda to gate on it: `_if=lambda: bool(host.get_fact(MyFact))`.

## Output & Callbacks

pyinfra doesn't immediately execute operations, meaning output is not available right away. It is possible to access this output at runtime by providing a callback function using the [`python.call`](operations/python.md#python-call) operation. Callback functions may also call other operations which will be immediately executed.
Why/how this works [is described here](deploy-process.md#detects-changes).

```python
from pyinfra import logger
from pyinfra.operations import python, server

result = server.shell(
    commands=["echo output"],
)
# result.stdout raises exception here, but works inside callback()

def callback():
    logger.info(f"Got result: {result.stdout}")

python.call(
    name="Execute callback function",
    function=callback,
)
```

There is also the possibility to use pyinfra's logging functionality which may be appropriate in certain situations.

```python
from pyinfra import logger
def ufw_usable(function code here)
is_ufw_usable = ufw_usable()
logger.info('Checking output of ufw_usable: {}'.format(is_ufw_usable))
```

Produces output similar to:

```
--> Preparing Operations...
    Loading: deploy_create_users.py
    Checking output of ufw_usable: None
    [multitest.example.com] Ready: deploy_create_users.py
```

## Include Files

Including files can be used to break out operations across multiple files. Files can be included using `local.include`.

```python
from pyinfra import local

# Include & call all the operations in tasks/install_something.py
local.include("tasks/install_something.py")
```

Additional data can be passed across files via the `data` param to parameterize tasks and is available in `host.data`. For example `tasks/create_user.py` could look like:

```python
from getpass import getpass

from pyinfra import host
from pyinfra.operations import server

group = host.data.get("group")
user = host.data.get("user")

server.group(
    name=f"Ensure {group} is present",
    group=group,
)
server.user(
    name=f"Ensure {user} is present",
    user=user,
    group=group,
)
```

And and be called by other deploy scripts or tasks:

```python
from pyinfra import local

for group, user in (("admin", "Bob"), ("admin", "Joe")):
    local.include("tasks/create_user.py", data={"group": group, "user": user})
```

See more in [examples: groups & roles](examples/groups_roles.md).

## The `config` Object

Like `host` and `inventory`, `config` can be used to set global defaults for operations. For example, to use sudo in all following operations:

```python
from pyinfra import config

config.SUDO = True

# all operations below will use sudo by default (unless overridden by `_sudo=False`)
```

!!! note "`config` vs per-operation kwargs vs plain Python variables"
    - **`config.X = ...`** sets the deploy-wide default for a pyinfra setting (e.g. `SUDO`, `SU_USER`, `REQUIRE_PYINFRA_VERSION`, connection timeouts). Use this for things that apply broadly, like *"this whole deploy runs with sudo"* or *"require pyinfra 3.x"*.
    - **Per-operation kwargs** (`apt.packages(..., _sudo=False)`) override the config default for just that call. Use these when one operation needs to deviate.
    - **Plain Python variables** (`APP_USER = "myapp"` at the top of a deploy file) are not config — they're just constants. Prefer host/group data (see [Inventory & Data](inventory-data.md)) when the value should vary by host.

    See [Global Arguments](arguments.md) for the full list of settings that can be set on `config`.

## Retry Functionality

Operations can be configured to retry automatically on failure using retry arguments:

```python
from pyinfra.operations import server

# Retry a flaky command up to 3 times with default 5 second delay
server.shell(
    name="Download file with retries",
    commands=["curl -o /tmp/file.tar.gz https://example.com/file.tar.gz"],
    _retries=3,
)

# Retry with custom delay between attempts
server.shell(
    name="Check service status with retries",
    commands=["systemctl is-active myservice"],
    _retries=2,
    _retry_delay=10,  # 10 second delay between retries
)

# Use custom retry condition to control when to retry
def retry_on_network_error(output_data):
    # Retry if stderr contains network-related errors
    for line in output_data["stderr_lines"]:
        if any(keyword in line.lower() for keyword in ["network", "timeout", "connection"]):
            return True
    return False

server.shell(
    name="Network operation with conditional retry",
    commands=["wget https://example.com/large-file.zip"],
    _retries=5,
    _retry_until=retry_on_network_error,
)
```

### Enforcing Requirements

The config object can be used to enforce a pyinfra version or Python package requirements. This can either be defined as a requirements text file path or simply a list of requirements.
For example, if you create a `requirements.py` file with:

```python
# Require a certain pyinfra version
config.REQUIRE_PYINFRA_VERSION = "~=3.0"

# Require certain packages
config.REQUIRE_PACKAGES = "requirements.txt"  # path is relative to the current working directory
config.REQUIRE_PACKAGES = [
    "pyinfra~=3.0",
]
```

And create a `requirements.txt` file with something like this:

```sh
pyinfra
```

Then modify the `nano.py` above to include these lines:

```python
from pyinfra import local
local.include("requirements.py")
```

## Examples

A great way to learn more about writing pyinfra deploys is to see some in action. Check out:

- [the pyinfra examples repository on GitHub](https://github.com/pyinfra-dev/pyinfra-examples)
