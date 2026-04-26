---
name: writing-operations
---

Patterns and conventions for writing pyinfra operations.

**Applies to:** `src/pyinfra/operations/**/*.py`

Operations live in `src/pyinfra/operations/` and are decorated with `@operation()`.
They are **generator functions** that yield shell commands — never execute them directly.

## Module structure

```python
"""
Short module docstring (displayed in docs).
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.something import SomeFact

from . import files  # reuse other operations via ._inner()
```

## Operation anatomy

```python
@operation()
def my_operation(
    required_arg: str,
    optional_arg: str | None = None,
    flag: bool = False,
):
    """
    One-line summary of what the operation does.

    + required_arg: description of this argument
    + optional_arg: description, mention the default behaviour
    + flag: description of what True enables
    """
    # 1. Query current state via facts (cached per deploy)
    current_state = host.get_fact(SomeFact)

    # 2. Decide if a change is needed
    if required_arg in current_state:
        host.noop(f"{required_arg} already present")
        return

    # 3. Yield shell command strings or Command objects
    yield f"some-command {required_arg}"
```

## Key rules

- **Always check facts first** — use `host.get_fact()` to read current state before yielding.
- **Use `host.noop()`** when no change is needed. Never return silently without a comment.
- **Yield, never execute** — operations are collected during prepare phase and run later.
- **Delegate to other operations** via `yield from other_op._inner(...)`, never call them directly.
- **`@operation(is_idempotent=False)`** only for commands that must always run (e.g. `exec`, `shell`).
- **Raise `OperationError`** for unrecoverable errors detected during prepare (wrong args, etc.).
- Avoid `subprocess`, `os.system`, or any direct execution inside an operation body.
- **Optional parameter defaults** must be `None`, not `""`. Older operations use `""` defaults; do not replicate this pattern.
- **Mirror the underlying CLI's flag names** when picking parameter names. Examples
  of the convention to follow for new code:
  - `systemd.service(daemon_reload=...)` → `systemctl daemon-reload`
  - `git.repo(rebase=..., depth=..., recursive_submodules=...)` → `git pull --rebase`,
    `git clone --depth`, `git submodule update --recursive`

  Convert the flag to `snake_case` and drop the leading dashes. Diverge only when
  the CLI name is ambiguous out of context, conflicts with a
  [global argument](../../../src/pyinfra/api/arguments.py) (e.g. `name`, `_sudo`),
  or is genuinely misleading. Document the mapping in the docstring when the rename
  is non-obvious.

## Reusing operations internally

```python
# Correct — use ._inner() to compose operations
yield from files.directory._inner(path="/etc/apt/keyrings", present=True)
yield from files.file._inner(path=dest, mode="644")

# Wrong — never call the operation directly (it wraps in a new operation context)
files.directory(path="/etc/apt/keyrings", present=True)  # DON'T DO THIS
```

## Temporary files and directories

```python
# Use host helpers — they produce unique names per host/run
temp_file = host.get_temp_filename("prefix")
temp_dir = host.get_temp_filename("gpg-keyserver")
```

## Shell commands and safety

User-supplied values must be composed using `StringCommand` + `QuoteString` / `MaskString`
from `pyinfra.api`. Do not use plain string formatting (e.g. `"rm -f {}".format(path)`)
for user-controlled values.

```python
# Simple string
yield "apt-get update"

# f-string for variable interpolation (quote user input)
yield f'gpg --dearmor -o "{dest}" "{src}"'

# Multi-step pipeline: use && to chain
yield f'curl -fsSL "{url}" | gpg --dearmor -o "{dest}"'

# Use StringCommand for pre-built command objects
from pyinfra.api import StringCommand, QuoteString
yield StringCommand("rm", "-f", QuoteString(user_path))
```

## Error handling

```python
# Raise OperationError for invalid arguments (detected at prepare time)
if src is None and keyserver is None:
    raise OperationError("Either src or keyserver must be provided")

# Use assertions sparingly — prefer explicit OperationError with a message
```

## Docstring format

pyinfra uses `+ param: description` bullets (parsed by
`scripts/generate_operations_docs.py`). Do not use Google/NumPy/Sphinx style — it
will silently break docs generation.

```python
"""
Summary line.

+ arg_name: description of argument
+ other_arg: description (mention default/None behaviour explicitly)

Example section heading:
    Relevant note about this group of args.

.. warning::
    Deprecation or danger notice.
"""
```

## Helpers in `util/`

- `src/pyinfra/operations/util/packaging.py` — `ensure_packages()` for generic package management
- `src/pyinfra/operations/util/docker.py` — helpers for Docker operations
- Add new helpers here when logic is shared across multiple operation modules.

## After adding an operation

1. Add fixtures in `tests/operations/<module>.<op>/` (see the `writing-operation-tests` skill).
2. Register the module in `pyinfra-metadata.toml` so docs generation picks it up.
3. Run `./scripts/generate_operations_docs.py` to update docs.
