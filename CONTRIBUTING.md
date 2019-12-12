# Contributing to pyinfra

Third party pull requests help expand pyinfra's functionality and are essential to it's continued growth. This guide should help get you started adding additional modules/facts to pyinfra.


## Dev setup

```sh
# Create a virtualenv
virtualenv /path/to/venv

# Clone the repo
git clone git@github.com:Fizzadar/pyinfra.git

# Install the package in editable mode with development requirements
pip install -e .[dev]
```


## Tests

Use `pytest` to run tests, or `pytest --cov` to run with coverage.


## Guides

+ [How to write modules](https://pyinfra.readthedocs.io/page/api/modules.html) (operations + facts)
+ [API reference](https://pyinfra.readthedocs.io/page/api/reference.html)


## Code

+ Always add tests for modules (operations + facts)
+ Keep code style consistent:
    - ~90 character lines
    - no hanging indents
    - single quotes everywhere possible
