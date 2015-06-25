## pyinfra.modules.pip

Manage pip packages. Compatible globally or inside a virtualenv.

Uses:

+ `pip`

##### function: packages

Manage pip packages.

```py
packages(
    packages=None,
    present=True,
    requirements=None,
    venv=None # a virtualenv root directory
)
```
