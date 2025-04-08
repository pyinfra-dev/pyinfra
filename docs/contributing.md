# Contributing

🎉 Thank you for taking the time to contribute to pyinfra! 🎉

Third party pull requests help expand pyinfra's functionality and are essential to its continued growth. This guide should help get you started adding additional operations, facts and other functionality to pyinfra.

## Guides

+ [How to write operations](api/operations)
+ [How to write facts](api/facts)
+ [How to write connectors](api/connectors)
+ [API reference](api/reference)

## Branches

+ There is a branch per major version, ie `3.x`, that tracks the latest release of that version
+ Changes should generally be based off the latest major branch, unless fixing an old version

## Dev Setup

```sh
# Create a virtualenv with your tool of choice
# python -m venv / pyenv virtualenv / virtualenv

# Clone the repo
git clone git@github.com:pyinfra-dev/pyinfra.git

# Install the package in editable mode with development requirements
cd pyinfra
pip install -e '.[dev]'
```

### Code Style & Type Checking

Code style is enforced via Black, isort and flake8. Types are checked with mypy currently, and pyright is recommended for local development though currently optional. There is a script to run the linting & type-checking:

```sh
scripts/dev-lint.sh
```

### Tests

GitHub will run all the test suites as part of any pull requests. There's a handy script that runs the unit tests:

```sh
scripts/dev-test.sh
```

To limit the pytests to a specific fact or operation:

```sh
# Only run fact tests for facts.efibootmgr.EFIBootMGR
pytest tests/test_facts.py -k "efibootmgr.EFIBootMGR"

# Only run operation tests for operations.selinux
pytest tests/test_operations.py -k "selinux."
```

#### End to End Tests

The end to end tests are also executed via `pytest` but not selected by default, options/usage:

```sh
# Run all the e2e tests (local, SSH, Docker)
scripts/dev-test-e2e.sh

# Run local e2e tests (works on Linux / MacOS, no Windows yet)
pytest -m end_to_end_local

# Run Docker and SSH e2e tests (Linux / MacOS with Docker installed)
pytest -m end_to_end_ssh
pytest -m end_to_end_docker
```

## Documentation

Documentation changes should be made in the [https://github.com/pyinfra-dev/pyinfa](pyinfra git repository) - the repository `docs.pyinfra.com` should
not be changed, it contains build artifacts.

### Generate Documentation

To generate:

```sh
scripts/build-public-docs.sh
```

To view ([localhost:8000](http://localhost:8000)):

```sh
python -m http.server -d docs/public/en/latest/
```
