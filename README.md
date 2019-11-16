<h1>
    <a href="https://pyinfra.readthedocs.io">
        <img src="docs/static/logo_full.png" height="48px" />
    </a>
</h1>

[![PyPI version](https://badge.fury.io/py/pyinfra.svg)](https://pypi.python.org/pypi/pyinfra) [![Travis.CI status](https://travis-ci.org/Fizzadar/pyinfra.svg?branch=develop)](https://travis-ci.org/Fizzadar/pyinfra)

pyinfra automates/provisions/manages/deploys infrastructure super fast at massive scale. It can be used for ad-hoc command execution, service deployment, configuration management and more. Core design features include:

+ 🚀 **Super fast** execution over thousands of targets with predictable performance
+ 🚨 **Instant debugging** with stdout + stderr output on error, and `-v` to print it always
+ 💻 **Agentless execution** by speaking native SSH/Docker/subprocess depending on the target
+ ❗️ **Two stage process** that enables `--dry` runs before making any changes
+ 📦 **Extendable** with _any_ Python package as configured & written in standard Python

When you run pyinfra you'll see something like ([non animated version](docs/static/example_deploy.png)):

<img width="100%" src="docs/static/example_deploy.gif" />

## Quickstart

pyinfra can be installed via pip:

```sh
pip install pyinfra
```

Now you can execute commands & operations over SSH:

```sh
# Execute an abitrary shell command
pyinfra my-server.net exec -- echo "hello world"

# Install iftop apt package if not present
pyinfra my-server.net apt.packages iftop sudo=true
```

These can then be saved to a _deploy file_, let's call it `deploy.py`:

```py
from pyinfra.modules import apt

apt.packages(
    {'Install iftop'},
    'iftop',
    sudo=True,
)
```

And executed with:

```sh
pyinfra my-server.net deploy.py
```

## Documentation

+ [Getting started](https://pyinfra.readthedocs.org/page/getting_started.html)
+ [Documentation](https://pyinfra.readthedocs.org)
+ [Example deploy](example)
+ [API Example](https://pyinfra.readthedocs.org/page/api/example.html)
+ [How the deploy works](https://pyinfra.readthedocs.org/page/deploy_process.html)
