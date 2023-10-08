<p align="center">
    <a href="https://pyinfra.com">
        <img src="https://pyinfra.com/static/logo_readme.png" alt="pyinfra" />
    </a>
</p>

<p align="center">
    <em>pyinfra automates infrastructure super fast at massive scale<br />ad-hoc command execution, service deployment, configuration management and more</em>
</p>

---

<p align="center">
    <a href="https://docs.pyinfra.com"><strong>Documentation</strong></a> &rArr;
    <a href="https://docs.pyinfra.com/page/getting-started.html"><strong>Getting Started</strong></a> &bull;
    <a href="https://docs.pyinfra.com/page/examples.html"><strong>Examples</strong></a> &bull;
    <a href="https://docs.pyinfra.com/page/support.html"><strong>Help & Support</strong></a> &bull;
    <a href="https://docs.pyinfra.com/page/contributing.html"><strong>Contributing</strong></a>
</p>

<p align="center">
    Chat (both bridged) &rArr;
    <a href="https://matrix.to/#/#pyinfra:matrix.org"><strong><code>#pyinfra</code> on Matrix</strong></a> &bull;
    <a href="https://discord.gg/w3XxuKw"><strong>Discord</strong></a>
</p>

---

Why pyinfra? Design features include:

+ 🚀 **Super fast** execution over thousands of hosts with predictable performance.
+ 🚨 **Instant debugging** with realtime stdin/stdout/stderr output (`-vvv`).
+ 🔄 **Idempotent operations** that enable diffs and `--dry` runs before executing any changes.
+ 📦 **Extendable** with _any_ Python package as configured & written in standard Python.
+ 💻 **Agentless execution** against SSH/Docker/subprocess/WinRM hosts.
+ 🔌 **Integrated** with Docker, Terraform, Vagrant/Mech & Ansible out of the box.

When you run pyinfra you'll see something like ([non animated version](https://pyinfra.com/static/example_deploy.png)):

<img width="100%" src="https://pyinfra.com/static/example_deploy.gif" />

## Quickstart

Install pyinfra with [`pipx`](https://pipxproject.github.io/pipx/) (recommended) or `pip`:

```
pipx install pyinfra
```

Now you can execute commands on hosts via SSH:

```sh
pyinfra my-server.net exec -- echo "hello world"
```

Or execute in Docker, on the local machine, and other [connectors](https://docs.pyinfra.com/page/connectors.html):

```sh
pyinfra @docker/ubuntu exec -- echo "Hello world"
pyinfra @local exec -- echo "Hello world"
```

As well as executing commands you can define state using [operations](https://docs.pyinfra.com/page/operations.html):

```sh
# Install iftop apt package if not present
pyinfra @docker/ubuntu apt.packages iftop update=true _sudo=true
```

Which can then be saved as a Python file like `deploy.py`:


```py
from pyinfra.operations import apt

apt.packages(
    name="Ensure iftop is installed",
    packages=['iftop'],
    update=True,
    _sudo=True,
)
```

The hosts can also be saved in a file, for example `inventory.py`:

```py
targets = ["@docker/ubuntu", "my-test-server.net"]
```


And executed together:

```sh
pyinfra inventory.py deploy.py
```

Now you know the building blocks of pyinfra! By combining inventory, operations and Python code you can deploy anything.

See the more detailed [getting started](https://docs.pyinfra.com/page/getting-started.html) or [using operations](https://docs.pyinfra.com/page/using-operations.html) guides. See how to use [inventory & data](https://docs.pyinfra.com/page/inventory-data.html), [global arguments](https://docs.pyinfra.com/page/arguments.html) and [the CLI](https://docs.pyinfra.com/page/cli.html) or check out the [documented examples](https://docs.pyinfra.com/page/examples.html).

---

<p align="center">
    <a href="https://pypi.python.org/pypi/pyinfra"><img alt="PyPI version" src="https://img.shields.io/pypi/v/pyinfra?color=blue"></a>
    <a href="https://pepy.tech/project/pyinfra"><img alt="PyPi downloads" src="https://pepy.tech/badge/pyinfra"></a>
    <a href="https://docs.pyinfra.com"><img alt="Docs status" src="https://img.shields.io/github/actions/workflow/status/Fizzadar/pyinfra/docs.yml?branch=2.x"></a>
    <a href="https://github.com/Fizzadar/pyinfra/actions?query=workflow%3A%22Execute+tests%22"><img alt="Execute tests status" src="https://img.shields.io/github/actions/workflow/status/Fizzadar/pyinfra/test.yml?branch=2.x"></a>
    <a href="https://codecov.io/github/Fizzadar/pyinfra"><img alt="Codecov Coverage" src="https://img.shields.io/codecov/c/gh/Fizzadar/pyinfra"></a>
    <a href="https://github.com/Fizzadar/pyinfra/blob/2.x/LICENSE.md"><img alt="MIT Licensed" src="https://img.shields.io/pypi/l/pyinfra"></a>
</p>
