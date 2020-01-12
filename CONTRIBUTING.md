# Contributing to pyinfra

Third party pull requests help expand pyinfra's functionality and are essential to it's continued growth. This guide should help get you started adding additional modules/facts to pyinfra.


## Dev Setup

```sh
# Create a virtualenv
virtualenv /path/to/venv

# Clone the repo
git clone git@github.com:Fizzadar/pyinfra.git

# Install the package in editable mode with development requirements
pip install -e .[dev]

# Configure git to use pre-commit hook
flake8 --install-hook git
```

## Running pyinfra from local directory
If you want to make changes to pyinfra and test it, you can follow the Dev Setup steps above then run:

```sh
python setup.py install
```

## Generate documentation locally

To generate:
```sh
scripts/build_docs.sh
```

To view (on mac):

```sh
open docs/build/index.html
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
