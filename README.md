<p align="center">
    <a href="https://pyinfra.com">
        <img src="https://pyinfra.com/static/logo_readme.png" alt="pyinfra" />
    </a>
</p>

<p align="center">
    <em>pyinfra automates infrastructure super fast at massive scale</em>
</p>

<p align="center">
    <a href="https://pypi.python.org/pypi/pyinfra"><img alt="PyPI version" src="https://img.shields.io/pypi/v/pyinfra?color=blue"></a>
    <a href="https://pepy.tech/project/pyinfra"><img alt="PyPi downloads" src="https://pepy.tech/badge/pyinfra"></a>
    <a href="https://docs.pyinfra.com"><img alt="Docs status" src="https://img.shields.io/github/workflow/status/Fizzadar/pyinfra/Generate%20&amp;%20Deploy%20Docs/master?label=docs"></a>
    <a href="https://github.com/Fizzadar/pyinfra/actions?query=workflow%3A%22Execute+tests%22"><img alt="Execute tests status" src="https://img.shields.io/github/workflow/status/Fizzadar/pyinfra/Execute%20tests/master?label=tests"></a>
    <a href="https://codecov.io/github/Fizzadar/pyinfra"><img alt="Codecov Coverage" src="https://img.shields.io/codecov/c/gh/Fizzadar/pyinfra"></a>
    <a href="https://github.com/Fizzadar/pyinfra/blob/develop/LICENSE.md"><img alt="MIT Licensed" src="https://img.shields.io/pypi/l/pyinfra"></a>
</p>

---

<p align="center">
    <a href="https://docs.pyinfra.com"><strong>Documentation</strong></a> &bull;
    <a href="https://docs.pyinfra.com/page/getting_started.html"><strong>Getting Started</strong></a> &bull;
    <a href="https://docs.pyinfra.com/en/1.x/examples.html"><strong>Examples</strong></a> &bull;
    <a href="https://docs.pyinfra.com/page/support.html"><strong>Help & Support</strong></a> &bull;
    <a href="https://docs.pyinfra.com/page/contributing.html"><strong>Contributing</strong></a>
</p>

---

pyinfra automates/provisions/manages/deploys infrastructure. It can be used for ad-hoc command execution, service deployment, configuration management and more. Design features include:

+ 🚀 **Super fast** execution over thousands of hosts with predictable performance.
+ 🚨 **Instant debugging** with stdout & stderr output on error or as required (`-v`|`-vv`|`-vvv`).
+ 📦 **Extendable** with _any_ Python package as configured & written in standard Python.
+ 💻 **Agentless execution** against SSH/Docker/subprocess/winrm hosts.
+ ❗️ **Two stage process** that enables `--dry` runs before executing any changes.
+ 🔌 **Integrated** with Docker, Vagrant/Mech & Ansible out of the box.

When you run pyinfra you'll see something like ([non animated version](https://pyinfra.com/static/example_deploy.png)):

<img width="100%" src="https://pyinfra.com/static/example_deploy.gif" />

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
