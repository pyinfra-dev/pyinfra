---
name: writing-operation-tests
---

JSON / YAML fixture format for operation unit tests.

**Applies to:** `tests/operations/**/*.{json,yaml}`

Operation tests live in `tests/operations/<module>.<function>/` as JSON or YAML files.
Each file is one test case. The test runner (`tests/test_operations.py`) discovers
them automatically via the `TestGenerator` metaclass (which is ignored by pytest
collection to avoid warnings).

**Prefer YAML for new fixtures.** To cover a new code path, add a fixture — do not
write a new Python test.

## Fixture schema (JSON)

```json
{
    "args": [],
    "kwargs": {
        "param_name": "value"
    },
    "facts": {
        "FactModule.FactClass": {
            "arg1=value1": <fact_return_value>
        }
    },
    "commands": [
        "shell command 1",
        "shell command 2"
    ]
}
```

## Fixture schema (YAML)

```yaml
args:
  - positional_arg
kwargs:
  param: value
facts:
  module.FactClass: {}          # dict of mock values keyed by object_id and attribute
commands:
  - shell command that should be produced
```

### Fields

| Field | Required | Description |
|---|---|---|
| `args` | Yes | Positional arguments to the operation (usually `[]`) |
| `kwargs` | Yes | Keyword arguments to the operation |
| `facts` | No | Facts to pre-populate in the cache |
| `commands` | Yes | Expected list of commands that the operation yields |
| `exception` | No | Class name (e.g. `"OperationError"`) or `{name, message}` of the expected exception |
| `noop_description` | No | Expected `host.noop()` description string |

### `facts` format

Keys use `"Module.Class"` notation matching the fact's Python path relative to
`pyinfra.facts`. Values are dicts keyed by `"arg=value"` argument strings:

```json
"facts": {
    "files.File": {
        "path=/etc/apt/keyrings/test.gpg": null
    },
    "files.Directory": {
        "path=/etc/apt/keyrings": null
    },
    "gpg.GpgKeyrings": {
        "arg=[[\"/etc/apt/keyrings\"]]": {}
    }
}
```

- `null` means the fact returned no result (e.g. file does not exist).
- Omitting a fact key means it will NOT be in the cache — the operation must not call it.
- For facts with no arguments, use `""` as the key: `{"": <value>}`.

### `commands` format

Each element is either:
- A **string** — a shell command matched verbatim.
- A **dict** — a special command type, e.g. a file upload:

```json
{"type": "put", "src": "local/path", "dest": "/remote/path", "mode": "644"}
```

### Error cases

Use `"exception"` instead of `"commands"` when the operation should raise:

```json
{
    "args": [],
    "kwargs": {},
    "exception": "OperationError"
}
```

## File naming

Name files descriptively after the scenario, using underscores:

```
tests/operations/gpg.key/
  local_file.json            # install from local .asc
  remote_url.json            # install from HTTPS URL
  keyserver_single.json      # single key from keyserver
  keyserver_multiple.json    # multiple keys from keyserver
  keyserver_idempotent.json  # key already present → no commands
  no_src_or_keyserver.json   # missing args → OperationError
  remove_file.json           # present=False
```

## Idempotency tests

Always add a `*_idempotent.json` or `*_existing.json` case where the facts show
the desired state is already reached, and `commands` is `[]`:

```json
{
    "args": [],
    "kwargs": {"name": "existing-package"},
    "facts": {
        "deb.DebPackages": {
            "": {"existing-package": {"version": "1.0"}}
        }
    },
    "commands": []
}
```

## Running

```bash
uv run pytest tests/test_operations.py -k "<module>.<op>"
```

## Tips

- Always include a test for the **happy path** (change needed) and **idempotent path** (no change).
- Include tests for **invalid inputs** that should raise `OperationError`.
- Reproduce real-world strings (e.g. exact `gpg` or `apt-get` command lines) — copy from
  actual command output, not guessed.
