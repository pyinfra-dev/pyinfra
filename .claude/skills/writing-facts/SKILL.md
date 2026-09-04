---
name: writing-facts
---

Patterns and conventions for writing pyinfra facts.

**Applies to:** `src/pyinfra/facts/**/*.py`

Facts live in `src/pyinfra/facts/` and inherit from `FactBase`. They query remote system
state by running a shell command and parsing its output.

## Module structure

```python
from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase
```

## Fact anatomy

```python
class MyFact(FactBase[ReturnType]):
    """
    Returns a description of what is returned.

    .. code:: python

        {"key": "value"}
    """

    # Simple facts: just set a command string
    command = "some-command --with-colons"

    # Or implement command() as a method when args are needed
    @override
    def command(self, arg1: str, arg2: str | None = None) -> str:
        return f"some-command {arg1}"

    # Optional: declare what must be installed for this fact to run
    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "some-binary"

    # Default value when the fact returns nothing / command fails
    default = dict  # or list, or None

    @override
    def process(self, output) -> ReturnType:
        result = {}
        for line in output:
            if not line or line.startswith("#"):
                continue
            # parse line…
        return result
```

## Key rules

- **`output` is a list of strings**, one per line, already stripped of the trailing newline.
- **Return structured data** — dicts, lists, or primitives. Avoid returning raw strings.
- **`default`** must be a callable (e.g. `dict`, `list`) or `None`. It is called when the
  command produces no output or the fact is not applicable.
- **`requires_command`** returns the binary that must exist on the remote host. Name it
  exactly as it appears in `PATH` (without arguments).
- **`check_preconditions`** returns `None` (proceed) or a reason string (skip with explanation).
  The framework is phase-aware: failures are silent during prepare and raised during execute.
- **`abstract = True`** marks a base class that is not directly usable as a fact.
- Use `from __future__ import annotations` and `@override` on every overridden method.

## Facts with arguments

When a fact accepts arguments, `command()` and `requires_command()` must accept the
same arguments:

```python
class FileSha256(FactBase[str | None]):
    @override
    def command(self, path: str) -> str:
        return f"sha256sum {path} 2>/dev/null | cut -d' ' -f1"

    @override
    def requires_command(self, path: str) -> str:
        return "sha256sum"
```

Call with: `host.get_fact(FileSha256, path="/etc/passwd")`

## Parsing patterns

```python
# Split on colon (GPG --with-colons, apt-cache, etc.)
bits = line.split(":")

# Split on first occurrence only (key: value pairs)
key, _, value = line.partition(":")

# Regex for complex formats
import re
match = re.match(r"^(\S+)\s+(\S+)", line)
if match:
    name, version = match.groups()
```

## Shared base classes

- **`GpgFactBase`** (`facts/gpg.py`) — base for facts that parse `gpg --with-colons` output.
  Override `key_record_type` / `subkey_record_type` to target pub/sec keys.
- **`FactBase`** — the universal base. Generic parameter `FactBase[T]` documents return type.

## Shell command robustness

Prefer the framework hooks over shell-level guards:

- **Missing binary** → declare `requires_command()`. The framework skips the fact
  (returning the `default`) when the binary is absent, instead of running the command.
- **Phase / context guards** (e.g. only on certain OS, only when a feature is enabled)
  → implement `check_preconditions()`.

Reserve shell guards for cases the framework hooks cannot express:

```python
# Suppress errors gracefully when files may not exist
command = "cat /etc/file 2>/dev/null || true"

# Guard glob expansion when directory may be empty
command = "ls /etc/apt/sources.list.d/*.list 2>/dev/null || true"
```

Do **not** use the legacy `! command -v binary || real-command` pattern in new
facts — use `requires_command()` instead. A few older facts still embed it; do
not replicate them.

## File-boundary marker pattern (multi-file parsing)

When a single fact command reads multiple files, use a marker line to separate them:

```python
@override
def command(self) -> str:
    return (
        "sh -c '"
        "for f in /etc/apt/sources.list.d/*.sources; do "
        '[ -e "$f" ] || continue; '
        'echo "##PYINFRA_FILE $f"; '
        'cat "$f"; '
        "echo; "
        "done'"
    )

@override
def process(self, output):
    current_file = None
    buffer = []

    def flush():
        nonlocal buffer, current_file
        if current_file and buffer:
            # parse buffer for current_file
            pass
        buffer = []

    for line in output:
        if line.startswith("##PYINFRA_FILE "):
            flush()
            current_file = line[15:].strip()
            continue
        buffer.append(line)

    flush()
```

Use `##PYINFRA_FILE` (not `##FILE`) as the marker prefix — it is unique enough to
avoid collision with legitimate file content.

## After adding a fact

1. Add fixtures in `tests/facts/<module>.<FactClass>/` (see the `writing-fact-tests` skill).
2. Register the module in `pyinfra-metadata.toml` so docs generation picks it up.
3. Run `./scripts/generate_facts_docs.py` to update docs.
