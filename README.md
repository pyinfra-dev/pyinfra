# pyinfra [![PyPI version](https://badge.fury.io/py/pyinfra.svg)](https://pypi.python.org/pypi/pyinfra) [![Travis.CI status](https://travis-ci.org/Fizzadar/pyinfra.svg?branch=develop)](https://travis-ci.org/Fizzadar/pyinfra)

pyinfra automates service deployment. It does this by diff-ing the state of the server with the state defined in the deploy script. Deploys are asyncronous and highly performant. The inventory & deploy are managed with pure Python, allowing for near-infinite extendability.

+ [Getting started](https://pyinfra.readthedocs.org/getting_started.html)
+ [Documentation](https://pyinfra.readthedocs.org)
+ [Example deploy](example)
+ [API Example](https://pyinfra.readthedocs.org/api_example.html)
+ [How the deploy works](https://pyinfra.readthedocs.org/deploy_process.html)

When you run pyinfra you'll see something like:

![](./docs/example_deploy.png)


## Design Features

pyinfra was designed from day one to enable ops to deploy things in a consistent, debuggable
and maintainable manner. Notable design decisions:

+ outputs shell commands and files to upload
+ two-step deploy that enables dry-runs
+ fail fast where possible (eg touching a directory)
+ `-v` means print out remote stdout & stderr in realtime
+ always print raw stderr on operation failure for _instant_ debugging
+ uses pure, 100% Python for the inventory and deploy scripts
    * with operations/hooks to safely use Python mid-deploy
+ properly agentless - even Python isn't required on the remote side (just a shell!)


## Development

pyinfra is still under heavy development, and while the CLI/API should be considered fairly
stable there's no guarantee of no breaking changes until `v1`. There are a number of critical
specifications to be properly fleshed out before the `v1` release:

+ spec/docs for roles/sub-deploys
+ spec/docs for extension modules/facts
+ spec/docs for extension deploys

To develop pyinfra itself:

```sh
# Create a virtualenv
venv create pyinfra

# Install pyinfra in dev mode, with dev requirements
pip install -e .[dev]
```

Use `nosetests` or the bundled helper script to run tests. This helper script also counts
coverage:

```sh
# Test everything (API, modules & facts)
scripts/test.sh

# Set individual bits
scripts/test.sh [api|modules|facts]
```
