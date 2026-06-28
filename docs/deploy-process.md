# How pyinfra Works

Every `pyinfra` run steps through five stages:

1. **Setup** — load the inventory file and any group/host data
2. **Connect** — open a connection (e.g. one SSH session) to each target host
3. **Prepare** — run the deploy code once per host to establish operation order and detect which operations will change each host
4. **Execute** — walk the operation list and, for each operation, generate and run its commands on every host
5. **Disconnect** — close the connections and emit the final report

Most of these are unsurprising; the interesting one is **prepare**, because it is the stage that determines the order operations run in. Your deploy file's Python runs once, during prepare, to establish that order; then each *operation* is re-evaluated individually during execute to produce the commands that actually run.

## The two-phase execution model { #detects-changes }

pyinfra is, at its core, a translator. Your Python deploy file is not run *on* the target host — it's run *locally*, once per host in the inventory, and the operations it calls turn into shell commands that pyinfra ships over the connection.

### Phase 1: prepare

For every host in the inventory pyinfra invokes your deploy code with the `host` context bound to that host. As your code calls operations like `apt.packages(...)`, each operation:

1. Reads the current state from the target by gathering any [facts](facts.md) it needs (e.g. `AptPackages` to see what is already installed). Facts open a channel on the existing connection, run a read-only shell command, and cache the parsed result for the rest of the deploy.
2. Diffs that state against the desired state you've described.
3. Determines whether it would produce any commands — pyinfra advances the operation just far enough to see its first command, then stops. It does **not** build or keep the full command list at this point.
4. Returns an `OperationMeta` handle with a `will_change` flag indicating whether the operation would change anything.

When the deploy file finishes, pyinfra knows the order operations appear in and which operations will change which hosts. What it has built is an **ordering**, not a stored list of commands. **No mutating commands have been sent to any target yet** — only fact-gathering reads.

### Phase 2: execute

pyinfra then walks the operations in order. For each operation it **re-evaluates** the operation against each host — re-running the operation's logic to generate its commands, then running them on every host that needs them, in parallel, and waiting for that operation to finish on all hosts before moving on to the next. The commands are produced here, at execute time, not replayed from prepare.

This means a host's connection lifecycle for a deploy is typically: one connection opens at stage 2, stays open for facts (prepare) and command execution (execute), and closes at stage 5. Individual operations open new channels over that single connection rather than fresh sessions per command.

### Why all this matters: ordering

A deploy file is written as if it were running against one host. But you usually have many. Consider this inventory:

```python
web_servers = ["web-01", "web-02", "web-03"]
db_server = ["db-01"]
```

…and this deploy:

```python
from pyinfra import host
from pyinfra.operations import apt

apt.packages(
    name="Install base debugging packages",
    packages=["htop", "iftop"],
    update=True,
    cache_time=3600,
)

if "db_server" in host.groups:
    apt.packages(
        name="Install postgres server",
        packages=["postgresql-server"],
    )

if "web_servers" in host.groups:
    apt.packages(
        name="Install nginx",
        packages=["nginx"],
    )
```

If pyinfra naively ran the whole deploy on each host in parallel, hosts could finish at different points and operations would interleave unpredictably — fine here, but breaks down as soon as one host depends on something an earlier operation on a *different* host did (e.g. webservers reading the database hostname). pyinfra avoids this by running each operation in lock-step across hosts: all hosts complete operation N (or fail it) before any host starts operation N+1. The schedule for the example above looks like:

```
- "Install base debugging packages" on web-01, web-02, web-03, db-01 (in parallel)
- "Install postgres server"         on db-01
- "Install nginx"                   on web-01, web-02, web-03 (in parallel)
```

Getting that ordering right is precisely what the prepare phase is for. pyinfra has to execute your deploy code first — running it through to the end on every host — to discover which operations each host needs, what order they appear in, and how they relate. Only then can it stitch the per-host orderings together into a single sequence to execute. This is why **deploy code always runs before any host is mutated**, and why a fact branched on in Python (`if host.get_fact(File, ...):`) reflects pre-deploy state rather than the running state at that point in the file. The next two subsections show the implications.

## When does this matter?

### Using Host Facts { #using-host-facts }

!!! caution
    Only use immutable facts in deploy code (installed OS, Arch, etc) unless you are absolutely sure they will not change.

Let's look at an example - the deploy code here is bad but highlights the ordering problems:

```python
from pyinfra import facts, host
from pyinfra.operations import apt
from pyinfra.facts.files import File

apt.packages(
    name="Install nginx",
    packages=["nginx"],
)

if host.get_fact(File, path="/etc/nginx/sites-enabled/default"):
    files.file(
        name="Remove nginx default site",
        path="/etc/nginx/sites-enabled/default",
        present=False,
    )
```

The critical thing to remember is that when you execute `pyinfra INVENTORY deploy.py` the deploy code is run *before* the operations are actually executed. This enables pyinfra to figure out the correct order for operations (see below for a detailed explanation).

The problem here is the conditional check:

```python
if host.get_fact(facts.files.File, path="/etc/nginx/sites-enabled/default"):
```

This gets executed *before* the `apt.packages` install, and evaluates to `False`. But at execution time this would actually become `True`. The solution is simple - rely on pyinfra's operations to describe the desired state and always call the second:

```python
from pyinfra import facts, host
from pyinfra.operations import apt, files

apt.packages(
    name="Install nginx",
    packages=["nginx"],
)

files.file(
    name="Remove nginx default site",
    path="/etc/nginx/sites-enabled/default",
    present=False,
)
```

In this case when the `files.file` operation is executed pyinfra will check if the file is present and remove it if so, and do nothing if not.

### Checking Operation Changes

!!! caution
    Always use the `_if` global argument when checking for previous operation changes.

Let's use a simple example as above with add a conditional reload based on the outcome of the `files.file` operation:

```python
from pyinfra import facts, host
from pyinfra.operations import apt, files, server

apt.packages(
    name="Install nginx",
    packages=["nginx"],
)

remove_default_site = files.file(
    name="Remove nginx default site",
    path="/etc/nginx/sites-enabled/default",
    present=False,
)

if remove_default_site.changed:
    server.service(
        name="Reload nginx",
        service="nginx",
        reloaded=True,
    )
```

As above, the problem here is again the conditional check:

```python
if remove_default_site.changed:
```

Since this gets executed before nginx is installed by `apt.packages` operation, the value of `remove_default_site.changed` at this stage is `False` but at execution time this would become `True`, exactly like the fact example above. The solution here is to use the `_if` global argument to delay the check until execution time:

```python
from pyinfra import facts, host
from pyinfra.operations import apt, files, server

apt.packages(
    name="Install nginx",
    packages=["nginx"],
)

remove_default_site = files.file(
    name="Remove nginx default site",
    path="/etc/nginx/sites-enabled/default",
    present=False,
)

server.service(
    name="Reload nginx",
    service="nginx",
    reloaded=True,
    _if=remove_default_site.did_change,
)
```

### Loops & Cycle Errors { #loops-cycle-errors }

In CLI mode `pyinfra` builds a single DAG to determine the order in which operations are executed. This usually produces the order a deploy author expects, but loops can make the same operation line appear multiple times with different per-host paths through the deploy. When those paths disagree about which operation must run first, the ordering graph contains a cycle and `pyinfra` raises a cycle error.

Use `host.loop` when a loop contains operations. This gives `pyinfra` the loop position as an ordering hint:

```python
from pyinfra import host
from pyinfra.operations import server

for i in host.loop(range(0, 2)):
    server.shell(
        name=f"Do a thing {i}",
        commands="ls",
    )
```

For example, this deploy can generate a cycle because the first operation only appears on `@local` during the first loop iteration:

```python
from pyinfra import host
from pyinfra.operations import server

for i in range(0, 2):
    if i > 0 or (i == 0 and host.name == "@local"):
        server.shell(
            name="A",
            commands="ls",
        )

    server.shell(
        name="B",
        commands="ls",
    )
```

The resulting per-host order is inconsistent:

```shell
# @local: A -> B -> A-1 -> B-1
# Other:       B -> A   -> B-1
```

Combining those host orders means `A` must run before `B` and `B` must run before `A`. Switching the loop to `host.loop` includes the loop position in the operation order and removes the ambiguity:

```python
from pyinfra import host
from pyinfra.operations import server

for i in host.loop(range(0, 2)):
    if i > 0 or (i == 0 and host.name == "@local"):
        server.shell(
            name="A",
            commands="ls",
        )

    server.shell(
        name="B",
        commands="ls",
    )
```

The graph can then be resolved consistently:

```shell
# @local: 0A -> 0B -> 1A -> 1B
# Other:        0B -> 1A -> 1B
```
