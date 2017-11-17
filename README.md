# pyinfra

[![PyPI version](https://badge.fury.io/py/pyinfra.svg)](https://pypi.python.org/pypi/pyinfra) [![Travis.CI status](https://travis-ci.org/Fizzadar/pyinfra.svg?branch=develop)](https://travis-ci.org/Fizzadar/pyinfra)

pyinfra manages the state of one or more servers. It can be used for app/service deployment, config management and ad-hoc command execution. Deploys are asynchronous, highly performant and can target thousands of hosts in parallel. The inventory of servers and deploy state are written in Python, allowing for near-infinite extendability. pyinfra is available via the command line and as a Python API.

+ [Getting started](https://pyinfra.readthedocs.org/page/getting_started.html)
+ [Documentation](https://pyinfra.readthedocs.org)
+ [Example deploy](example)
+ [API Example](https://pyinfra.readthedocs.org/page/api/example.html)
+ [How the deploy works](https://pyinfra.readthedocs.org/page/deploy_process.html)

When you run pyinfra you'll see something like:

![](docs/example_deploy.png)


## Design Features

pyinfra was designed to enable us to deploy things in a consistent, debuggable and maintainable manner. Notable design decisions:

+ properly agentless - even Python isn't required on the remote side (just a shell!)
+ always print raw stderr on operation failure for _instant_ debugging
+ `-v` means print out remote stdout & stderr in realtime
+ outputs shell commands and files to upload
+ two-step deploy that enables dry-runs
+ fail fast where possible (eg touching a directory)
+ uses pure, 100% Python for the inventory and deploy scripts
    * with operations/hooks to safely use Python mid-deploy
