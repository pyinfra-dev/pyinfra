<h1>
    <a href="https://pyinfra.com">
        <img src="https://raw.githubusercontent.com/Fizzadar/pyinfra/master/docs/static/logo_full.png" height="48px" />
    </a>
</h1>

[![PyPI version](https://img.shields.io/pypi/v/pyinfra?color=blue)](https://pypi.python.org/pypi/pyinfra)
[![PyPi downloads](https://pepy.tech/badge/pyinfra)](https://pepy.tech/project/pyinfra)
[![Docs status](https://img.shields.io/github/workflow/status/Fizzadar/pyinfra/Generate%20&%20Deploy%20Docs/master?label=docs)](https://docs.pyinfra.com)
[![Execute tests status](https://img.shields.io/github/workflow/status/Fizzadar/pyinfra/Execute%20tests/master?label=tests)](https://github.com/Fizzadar/pyinfra/actions?query=workflow%3A%22Execute+tests%22)
[![Codecov Coverage](https://img.shields.io/codecov/c/gh/Fizzadar/pyinfra)](https://codecov.io/github/Fizzadar/pyinfra)
[![MIT Licensed](https://img.shields.io/pypi/l/pyinfra)](https://github.com/Fizzadar/pyinfra/blob/develop/LICENSE.md)

pyinfra automates/provisions/manages/deploys infrastructure super fast at massive scale. It can be used for ad-hoc command execution, service deployment, configuration management and more. Core design features include:

+ 🚀 **Super fast** execution over thousands of hosts with predictable performance.
+ 🚨 **Instant debugging** with stdout & stderr output on error or as required (`-v`|`-vv`|`-vvv`).
+ 📦 **Extendable** with _any_ Python package as configured & written in standard Python.
+ 💻 **Agentless execution** against SSH/Docker/subprocess/winrm hosts.
+ ❗️ **Two stage process** that enables `--dry` runs before executing any changes.
+ 🔌 **Integrated** with Docker, Vagrant/Mech & Ansible out of the box.

When you run pyinfra you'll see something like ([non animated version](https://raw.githubusercontent.com/Fizzadar/pyinfra/master/docs/static/example_deploy.png)):

<img width="100%" src="https://raw.githubusercontent.com/Fizzadar/pyinfra/master/docs/static/example_deploy.gif" />

## Quickstart

pyinfra can be installed via pip:

```sh
pip install pyinfra
```

Now you can execute commands & operations over SSH:

```sh
# Execute an arbitrary shell command
pyinfra my-server.net exec -- echo "hello world"

# Install iftop apt package if not present
pyinfra my-server.net apt.packages iftop sudo=true update=true
```

These can then be saved to a _deploy file_, let's call it `deploy.py`:

```py
from pyinfra.operations import apt

apt.packages(
    name='Ensure iftop is installed',
    packages=['iftop'],
    sudo=True,
    update=True,
)
```

And executed with:

```sh
pyinfra my-server.net deploy.py
```

or

```sh
pyinfra @docker/ubuntu deploy.py
```

## [Documentation](https://docs.pyinfra.com)

+ [Getting started](https://docs.pyinfra.com/page/getting_started.html)
+ [Writing deploys](https://docs.pyinfra.com/page/deploys.html)
+ [Using the CLI](https://docs.pyinfra.com/page/cli.html)
+ [Connectors](https://docs.pyinfra.com/page/connectors.html)
