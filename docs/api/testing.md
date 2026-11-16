# Testing Deploys

The [`@fake` connector](../connectors/fake.md) can run a deploy without connecting to or changing a real target. It simulates shell commands and file transfers, and records shell commands for test assertions.

For tests of individual facts and operations, use the [pyinfra-testing harness](https://github.com/pyinfra-dev/pyinfra-testing). Use `@fake` when you want to test a complete deploy through the API.

## Disable simulated delays in tests

By default, every simulated shell command and file transfer sleeps for **0.5 seconds plus random jitter of up to 0.4 seconds**. This makes demos and progress bars behave like a real deploy. Fact commands and uploads count towards this delay, so a deploy with several `file.template` operations can take several seconds.

Set both `fake_delay` and `fake_delay_jitter` to `0` in the fake host data for instant tests:

```python
{
    "fake_delay": 0,
    "fake_delay_jitter": 0,
}
```

Setting only `fake_delay=0` is not enough because the jitter remains active.

You can also change the defaults for every fake host with environment variables:

```sh
PYINFRA_FAKE_DELAY=0 PYINFRA_FAKE_DELAY_JITTER=0 pytest
```

Host data takes precedence over the environment defaults.

## Example deploy test

This example stubs the `Os` fact, runs a deploy, checks the operation result, and asserts the shell commands that ran:

```python
from pyinfra import host
from pyinfra.api import Config, Inventory, State, deploy
from pyinfra.api.connect import connect_all
from pyinfra.api.deploy import add_deploy
from pyinfra.api.operations import run_ops
from pyinfra.facts.server import Os
from pyinfra.operations import server


@deploy("Example")
def example_deploy():
    if host.get_fact(Os) == "Linux":
        server.shell(commands=["echo linux"])


def test_example_deploy():
    inventory = Inventory(([
        ("@fake/test", {
            "fake_responses": {"uname -s": "Linux"},
            "fake_delay": 0,
            "fake_delay_jitter": 0,
        }),
    ], {}))
    state = State(inventory, Config())

    connect_all(state)
    add_deploy(state, example_deploy)
    run_ops(state)

    fake_host = inventory.get_host("@fake/test")

    assert state.results[fake_host].success_ops == 1
    assert state.results[fake_host].error_ops == 0
    assert fake_host.connector.executed_commands == [
        "uname -s",
        "echo linux",
    ]
```

The first recorded command gathers the fact, and the second comes from the operation. `executed_commands` records shell commands only. It does not record high-level operation calls or file transfers. Use `state.results` for operation result counts and `state.ops` for the scheduled per-host operation data.

See the [`@fake` connector reference](../connectors/fake.md) for all response formats, including standard error, failures, and regular expression command matching.
