---
name: writing-fact-tests
---

JSON / YAML fixture format for fact unit tests.

**Applies to:** `tests/facts/**/*.{json,yaml}`

Fact tests live in `tests/facts/<module>.<FactClass>/` as JSON or YAML files.
Each file is one test case. The test runner (`tests/test_facts.py`) discovers
them automatically via the `TestGenerator` metaclass (which is ignored by pytest
collection to avoid warnings).

**Prefer YAML for new fixtures.** To cover a new code path, add a fixture — do not
write a new Python test.

## Fixture schema (JSON)

```json
{
    "command": "the shell command the fact produces",
    "requires_command": "binary-name",
    "arg": [<positional_args_list>],
    "output": [
        "line 1 of command stdout",
        "line 2 of command stdout"
    ],
    "fact": <expected_return_value>
}
```

## Fixture schema (YAML)

```yaml
command: shell command the fact runs
requires_command: binary               # optional
output: |
  raw stdout to parse
fact:
  item:
    key: value                         # expected return value of process()
```

### Fields

| Field | Required | Description |
|---|---|---|
| `command` | Yes | Exact string returned by `fact.command(...)` |
| `requires_command` | No | Exact string returned by `fact.requires_command(...)` |
| `arg` | No | List of positional arg lists, one per call variant. Omit if the fact takes no args |
| `output` | Yes | Simulated stdout lines (list of strings, no trailing newlines) |
| `fact` | Yes | Expected return value of `fact.process(output)` |

### `arg` format

For facts that take arguments, `arg` is a list of argument lists:

```json
"arg": [
    ["/etc/apt/trusted.gpg.d", "/etc/apt/keyrings"]
]
```

For facts with no arguments, omit `arg` entirely.

### `output` format

Each string is one line of stdout. Empty strings represent blank lines.
Use real command output whenever possible — copy from an actual system.

```json
"output": [
    "##PYINFRA_FILE /etc/apt/sources.list",
    "deb http://archive.ubuntu.com/ubuntu focal main",
    ""
]
```

### `fact` format

The `fact` field must exactly match what `fact.process(output)` returns.

For facts that return lists of dataclasses with dict-like access (e.g. `AptRepo`),
serialize each item as a plain dict:

```json
"fact": [
    {
        "type": "deb",
        "url": "http://archive.ubuntu.com/ubuntu",
        "distribution": "focal",
        "components": ["main"],
        "options": {}
    }
]
```

## File naming

Name files descriptively after the scenario being tested:

```
tests/facts/apt.AptSources/
  sources.json                     # standard .list file with mixed entries
  component_with_number.json       # component name contains a digit
  deb822_sources.json              # .sources (deb822) format, multi-stanza
  deb822_enabled_no.json           # Enabled: no → excluded from results
  deb822_multi_uris_suites.json    # multiple URIs and Suites → cartesian expansion
  deb822_malformed.json            # missing required field → empty result
  deb822_inline_gpg_key.json       # Signed-By with inline PGP block (continuation lines)
  deb822_trusted.json              # Trusted: yes option
```

## Coverage checklist for a new fact

| Scenario | File suffix |
|---|---|
| Typical happy-path output | `<name>.json` |
| Empty output (nothing installed/configured) | `empty.json` |
| Malformed or unexpected output | `malformed.json` or `bad_output.json` |
| Output with comments / blank lines | `with_comments.json` |
| Args variation (if fact takes args) | `with_args.json` |

## Multi-file parsing (##PYINFRA_FILE marker)

When a fact uses the file-boundary marker pattern, each test output must include
the `##PYINFRA_FILE` marker lines, and the `command` field must match the exact
shell command emitted by the fact:

```json
{
    "output": [
        "##PYINFRA_FILE /etc/apt/sources.list",
        "deb http://example.com/debian bookworm main",
        ""
    ],
    "command": "sh -c 'for f in /etc/apt/sources.list ...; do ...; echo \"##PYINFRA_FILE $f\"; ...; done'",
    "fact": [...]
}
```

## Running

```bash
uv run pytest tests/test_facts.py -k "<FactClass>"
```

## Tips

- Copy `command` verbatim from `fact.command()` — run `python3 -c "from pyinfra.facts.X import Y; print(Y().command())"` if unsure.
- Use real-world output samples (from actual machines) for believable test data.
- For dataclass-returning facts with dict-like access, the serializer calls `to_json()` — make sure the expected dict matches that method's output exactly.
- When adding a new test file, run `uv run pytest tests/test_facts.py -k "ClassName"` to validate immediately.
