# Contributing to pyinfra

Third party pull requests help expand pyinfra's functionality and are essential to it's continued growth. This guide should help get you started adding additional modules/facts to pyinfra.


## Dev setup

```
# Create a virtualenv
virtualenv /path/to/venv

# Clone the repo
git clone git@github.com:Fizzadar/pyinfra.git

# Install the package in "development mode"
pip install -e .
```


## Guides

+ [How to write operations](https://pyinfra.readthedocs.io/en/latest/api/operations.html)
+ [How to write facts](https://pyinfra.readthedocs.io/en/latest/api/facts.html)
+ [API reference](https://pyinfra.readthedocs.io/en/latest/api/reference.html)


## Code

+ Always add tests for operations/facts
+ Keep code style consistent:
    - ~90 character lines
    - no hanging indents
    - single quotes everywhere possible
