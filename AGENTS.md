# AGENTS.md

This file provides guidance to coding agents, like Claude Code (claude.ai/code), when working with 
code in this repository.

## About pyinfra

pyinfra turns Python code into shell commands and runs them on servers. Think Ansible, but Python
instead of YAML, and much faster. It supports SSH, local machine, Docker, and more via connectors.

## Development Setup

```bash
uv sync  # Install all dependencies into managed venv
```

## Common Commands

```bash
# Run tests
scripts/dev-test.sh
# or directly:
uv run pytest --cov --disable-warnings -m 'not end_to_end'

# Run fixtures for a single operation or fact
uv run pytest tests/test_operations.py -k "apt.packages"
uv run pytest tests/test_facts.py -k "LinuxHardware"

# End-to-end tests (require Docker/SSH/local targets)
uv run pytest -m end_to_end_local
uv run pytest -m end_to_end_docker

# Lint and type check
scripts/dev-lint.sh
# Individually:
uv run ruff check
uv run ruff format --check
uv run mypy
uv run python scripts/lint_arguments_sync.py

# Auto-format
scripts/dev-format.sh
```

## Architecture

The repo has two top-level packages under `src/`:

- **`pyinfra/`** — core library (operations, facts, connectors, API)
- **`pyinfra_cli/`** — CLI wrapper using Click + gevent

### Core Concepts

**Operations** (`src/pyinfra/operations/`) — Declarative functions (e.g. `apt.packages`,
`files.put`) that describe desired state. Each operation uses the `@operation` decorator from
`api/operation.py`, generates a list of commands, and is idempotent. Operations call facts to
read current state, then return commands to reach desired state.

**Facts** (`src/pyinfra/facts/`) — Read system state (e.g. `AptPackages`, `LinuxHardware`). Each
fact is a class extending `FactBase` with a `command` attribute and a `process()` method that
parses command output. Facts are cached per-host per-run.

**Connectors** (`src/pyinfra/connectors/`) — Abstractions for how to connect to and execute on a
target (SSH, local, Docker, chroot, Terraform, Vagrant, etc.). New connectors should be separate
packages, not added to this repo.

**API** (`src/pyinfra/api/`) — The core engine:
- `state.py` — Global deploy state, callbacks, host grouping
- `host.py` — Per-host metadata and fact access
- `inventory.py` — Collection of hosts and groups
- `operation.py` — `@operation` decorator that wraps functions into deploy operations
- `operations.py` — Execution engine that runs operations across hosts
- `command.py` — Command types: `StringCommand`, `FileUploadCommand`, `RsyncCommand`,
  `QuoteString`, `MaskString`, etc.
- `facts.py` — Fact base classes and execution logic
- `deploy.py` — `@deploy` decorator for grouping operations
- `connect.py` — Connector lifecycle (connect/disconnect)
- `config.py` — `Config` object with all configuration options
- `arguments.py` / `arguments_typed.py` — Global operation arguments (e.g. `_sudo`, `_su_user`);
  **these two files must stay in sync** — CI enforces this via `scripts/lint_arguments_sync.py`,
  so touching one requires touching the other
- `output.py` — Pluggable output functions (decoupled from Click for testability)

**Context** (`src/pyinfra/context.py`) — Thread-local (gevent-safe) context objects: `host`,
`state`, `config`, `inventory`. Operations access the current host via `pyinfra.context.host`
rather than explicit passing.

**Concurrency** — Uses gevent greenlets for parallel host execution. `pyinfra_cli/main.py`
monkey-patches stdlib at startup.

### Adding Operations / Facts

Operations and facts are auto-discovered from their respective directories. A new
`src/pyinfra/operations/mytool.py` is immediately available as `from pyinfra.operations import
mytool`.

- Operations must be idempotent and use facts to check current state
- Facts must implement `command` (shell command to run) and `process(output)` (parse result)
- Both need corresponding tests (see fixture convention below)
- Every operation/fact module must be registered in `pyinfra-metadata.toml` as a plugin with
  tags; omitting this won't break tests but will break docs generation

**Operation / fact tests are YAML or JSON fixtures, not Python tests.** Drop a file under
`tests/operations/<module>.<op>/` or `tests/facts/<module>.<Fact>/` — it is auto-discovered by
the `testgen` metaclass. Prefer YAML for new fixtures. To cover a new code path, add a fixture —
do not write a new Python test.

Operation fixture structure (`tests/operations/<module>.<op>/<name>.yaml`):

```yaml
args:
  - positional_arg
kwargs:
  param: value
facts:
  module.FactClass: {}          # a dict of mock values keyed by object_id and attribute
commands:
  - shell command that should be produced
```

Optional keys: `exception` (e.g. `{name: OperationError, message: "..."}`), `noop_description`.

Fact fixture structure (`tests/facts/<module>.<Fact>/<name>.yaml`):

```yaml
command: shell command the fact runs
requires_command: binary               # optional
output: |
  raw stdout to parse
fact:
  item:
    key: value                         # expected return value of process()
```

**Docstring format** — pyinfra uses `+ param: description` bullets (parsed by
`scripts/generate_operations_docs.py`). Do not use Google/NumPy/Sphinx style — it will silently
break docs generation.

**Shell safety** — user-supplied values must be composed into shell commands using `StringCommand`
+ `QuoteString` / `MaskString` from `pyinfra.api`. Do not use plain string formatting (e.g.
`"rm -f {}".format(path)`) for user-controlled values.

**Optional parameter defaults** — optional parameters must default to `None`, not `""`. Older
operations in the codebase use `""` defaults; do not replicate this pattern.

## Branch Strategy

PRs target the latest major branch (`3.x`). One branch per major version exists (`2.x`, `1.x`,
etc.).

## PR Checklist

- Tests pass (`scripts/dev-test.sh`)
- Lint/types pass (`scripts/dev-lint.sh`)
- New operations/facts include tests and documentation
