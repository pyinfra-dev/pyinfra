# Using the API

In addition to [the pyinfra CLI](../cli.md), pyinfra provides a full Python API. As of `v3` this API can be considered mostly stable. See [the API reference](reference.md).

You can also reference [pyinfra's own main.py](https://github.com/pyinfra-dev/pyinfra/blob/3.x/src/pyinfra_cli/main.py), and the [pyinfra API source code](https://github.com/pyinfra-dev/pyinfra/tree/3.x/src/pyinfra/api).

## Flow overview

A programmatic pyinfra run does the same five stages described in [How pyinfra Works](../deploy-process.md), but you drive them yourself:

1. **Build the inventory** — `Inventory((hosts_list, group_data_dict))`.
2. **Build the config** — `Config(SUDO=True, ...)` (any [global argument](../arguments.md) defaults).
3. **Build the state** — `State(inventory=inventory, config=config)`. This is the object passed through everything else.
4. **Connect** — `connect_all(state)` opens connections to every host in the inventory.
5. **Schedule operations** — call `add_op(state, op_func, **kwargs)` once per operation. Each call runs the operation function across all hosts in the prepare phase and returns a dict of `{host: OperationMeta}`.
6. **Execute** — `run_ops(state)` ships the scheduled commands to the hosts and returns when they've finished.
7. (Optional) **Read facts** — `get_facts(state, FactClass)` runs a fact on every host and returns a dict of `{host: value}`.

A few things worth knowing:

- **`add_op` is API-mode only.** It raises if called inside a CLI deploy. Inside a CLI deploy you just call the operation directly — `apt.packages(...)` — and pyinfra's wrapper takes care of the same scheduling internally.
- **You don't have to set `state.current_stage` manually.** The flag `pyinfra.is_cli` is `False` by default (only the CLI flips it to `True`), and the stage-transition guards on operations only fire when `is_cli` is true. `add_op` handles the `ctx_state` / `ctx_host` context-manager bookkeeping for you.
- **Look up hosts via the inventory**, not via `state`. The handle you keep is `inventory` — use `inventory.get_host(name)` to fetch the `Host` object you need to index into an `add_op` result.

## Basic Localhost Example

```python
from pyinfra.api import Config, Inventory, State
from pyinfra.api.connect import connect_all
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.facts import get_facts
from pyinfra.facts.server import Os
from pyinfra.operations import server

# Define your inventory (@local means execute on localhost using subprocess)
# https://docs.pyinfra.com/en/3.x/apidoc/pyinfra.api.inventory.html
inventory = Inventory((["@local"], {}))

# Define any config you need
# https://docs.pyinfra.com/en/3.x/apidoc/pyinfra.api.config.html
config = Config(SUDO=True)

# Set up the state object
# https://docs.pyinfra.com/en/3.x/apidoc/pyinfra.api.state.html
state = State(inventory=inventory, config=config)

# Connect to all the hosts
connect_all(state)

# Start adding operations
result1 = add_op(
    state,
    server.user,
    user="pyinfra",
    home="/home/pyinfra",
    shell="/bin/bash",
)
result2 = add_op(
    state,
    server.shell,
    name="Run some shell commands",
    commands=["whoami", "echo $PATH", "bash --version"]
)

# And finally we run the ops
run_ops(state)

# add_op returns {host: OperationMeta}, letting you access stdout, stderr, etc. after they run
host = inventory.get_host('@local')
print(result1[host].did_change, result1[host].stdout, result1[host].stderr)
print(result2[host].did_change, result2[host].stdout, result2[host].stderr)

# We can also get facts for all the hosts
# https://docs.pyinfra.com/en/3.x/apidoc/pyinfra.api.facts.html
print(get_facts(state, Os))
```

## Observing a run with callbacks

`state.add_callback_handler` lets you subscribe to lifecycle events — connection, per-host operation start/success/error/retry, operation start/end — without writing your own scheduler. This is the hook to use for telemetry, custom progress bars, or pushing results into your own systems.

```python
import time
from pyinfra.api import BaseStateCallback

class TimingCallback(BaseStateCallback):
    def __init__(self):
        self.timings = {}

    def operation_host_start(self, state, host, op_hash):
        self.timings.setdefault(op_hash, {})[host] = {"start": time.monotonic()}

    def operation_host_success(self, state, host, op_hash, retry_count=0):
        self.timings[op_hash][host]["end"] = time.monotonic()

    def operation_host_error(self, state, host, op_hash, retry_count=0, max_retries=0):
        self.timings[op_hash][host]["error"] = True

timings = TimingCallback()
state.add_callback_handler(timings)

run_ops(state)
# timings.timings now holds per-host start/end times for every operation
```

The available hooks are defined on `BaseStateCallback` — subclass it and override only the ones you care about. The current set covers host connect/disconnect, operation start/end, and per-host operation start/success/error/retry. See [`pyinfra.api.state.BaseStateCallback`](reference.md) for the full signature list.
