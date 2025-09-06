# Contributing

🎉 Thank you for taking the time to contribute to pyinfra! 🎉

Third party pull requests help expand pyinfra's functionality and are essential to its continued growth. This guide should help get you started adding additional operations, facts and other functionality to pyinfra.

## Guides

+ [How to write operations](api/operations)
+ [How to write facts](api/facts)
+ [How to write connectors](api/connectors) - note that new connectors **will not be merged to pyinfra**, instead they should be provided as a separate installable package. PR's that link to these packages in the docs very welcome.
+ Low level [API reference](api/reference) - this is pyinfra's internal APIs and does not come with the same compatibility guarantees as facts & operations - ie expect breaking changes on non-major versions.

## Branches

+ There is a branch per major version, ie `3.x`, that tracks the latest release of that version
+ Changes should generally be based off the latest major branch, unless fixing an old version

## Dev Setup

First, install [uv](https://docs.astral.sh/uv/).

Then, set up a development environment:

```sh
# There is no need to create a virtualenv, uv will do that for you

# Clone the repo
git clone git@github.com:pyinfra-dev/pyinfra.git

# Install the package in editable mode with development requirements
cd pyinfra
uv sync
```

### Code Style & Type Checking

Code style is enforced via Black, isort and flake8. Types are checked with mypy currently, and pyright is recommended for local development though currently optional. There is a script to run the linting & type-checking:

```sh
scripts/dev-lint.sh
```

### Commit Messages

Please try to use consistent commit messages, look at the [recent history](https://github.com/pyinfra-dev/pyinfra/commits/) for examples. PRs that follow this will be rebased, PRs that do not will be squashed.

### Tests

GitHub will run all the test suites as part of any pull requests. There's a handy script that runs the unit tests:

```sh
scripts/dev-test.sh
```

To limit the pytests to a specific fact or operation:

```sh
# Only run fact tests for facts.efibootmgr.EFIBootMGR
uv run pytest tests/test_facts.py -k "efibootmgr.EFIBootMGR"

# Only run operation tests for operations.selinux
uv run pytest tests/test_operations.py -k "selinux."
```

#### End to End Tests

The end to end tests are also executed via `pytest` but not selected by default, options/usage:

```sh
# Run all the e2e tests (local, SSH, Docker)
scripts/dev-test-e2e.sh

# Run local e2e tests (works on Linux / MacOS, no Windows yet)
uv run pytest -m end_to_end_local

# Run Docker and SSH e2e tests (Linux / MacOS with Docker installed)
uv run pytest -m end_to_end_ssh
uv run pytest -m end_to_end_docker
```

## Documentation

Documentation changes should be made in the [pyinfra git repository](https://github.com/pyinfra-dev/pyinfra) - the repository `docs.pyinfra.com` should
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
