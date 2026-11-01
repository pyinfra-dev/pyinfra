# Debugging Deploys

pyinfra deploys are designed to be safe to run repeatedly. A useful debugging loop is to inspect
the current host state, preview the deploy, add focused logging, and then run the deploy again.

## Inspect the inputs and plan

Start by checking the inventory and the facts used by the deploy:

```sh
# Show the resolved hosts, groups, and data
pyinfra inventory.py debug-inventory

# Collect a fact directly
pyinfra inventory.py fact server.LinuxName
```

Then preview the operations without changing the hosts:

```sh
pyinfra inventory.py deploy.py --debug-operations
pyinfra inventory.py deploy.py --dry
```

Increase verbosity to see more detail. `-v` includes collected facts and no-op information,
`-vv` includes the commands sent to hosts, and `-vvv` includes command output in real time. Use
`--debug` when you also need pyinfra's internal debug messages.

## Log values from deploy code

Use pyinfra's logger to inspect Python values while a deploy is being prepared:

```python
from pyinfra import host, logger
from pyinfra.facts.server import LinuxDistribution

distribution = host.get_fact(LinuxDistribution)
logger.info("Distribution data: %r", distribution)
```

Logging keeps diagnostic output with pyinfra's normal output. Avoid logging secrets or other
sensitive host data.

Do not add an operation such as `server.shell` merely to print a Python value. Operations run on
the target host and are deferred until the execution phase, so they do not behave like `print()`
statements in deploy code.

## Account for the execution model

pyinfra first runs deploy code for each host to gather facts and prepare an ordered set of
operations. It then executes those operations across the hosts. Consequently:

- facts read during preparation describe the host before this deploy's operations run;
- the output of an operation is not available immediately after calling it; and
- execution may be concurrent across hosts, so stepping through a deploy in an interactive
  debugger does not reliably represent the order of remote work.

Use [facts](facts.md) to inspect current host state. If later Python code must consume an
operation's output, use an execution-time callback as described in
[Output & Callbacks](using-operations.md#output--callbacks). For conditions that depend on an
earlier operation, use the `_if` callback described in
[Change Detection](using-operations.md#change-detection).

Keep the diagnostic change small, rerun the deploy, and remove or reduce temporary logging once
the behavior is understood.
