## Summary

Allow Docker-compatible CLI (e.g. Podman) to replace Docker via a `docker_cmd` parameter on all Docker operations, plus a new `pyinfra.operations.podman` proxy module that routes every command through `podman` instead of `docker`.

### Changes

**`pyinfra/operations/docker.py`** (commit `9fffb567`)
- Added `docker_cmd: str = "docker"` parameter to all 10 operations: `container`, `image`, `build`, `volume`, `network`, `prune`, `plugin`, `login`, `logout`, `compose`
- `build_cmd` now derives from `docker_cmd` when not explicitly provided (`f"{docker_cmd} build"`)
- `compose` keeps `compose_command: str = "docker compose"` (unchanged — already switchable)
- All operations pass `docker_cmd` through to generated `StringCommand`s and `host.get_fact(...)` calls
- All `docker_cmd` parameters documented in operation docstrings (`+ docker_cmd: Docker-compatible CLI to substitute for ``docker`` (e.g. ``podman``)`)
- `login` docstring: removed hardcoded ``docker login`` reference in prose
- `DockerSystemInfo.command()` now respects `docker_cmd` like `requires_command()` already did

**`pyinfra/operations/util/docker.py`** (commit `bf67c22e`)
- All 16 command builders (`_create_container`, `_remove_container`, `_start_container`, `_stop_container`, `_pull_image`, `_remove_image`, `_prune_command`, `_create_volume`, `_remove_volume`, `_create_network`, `_remove_network`, `_install_plugin`, `_remove_plugin`, `_enable_plugin`, `_disable_plugin`, `_set_plugin_options`) accept `docker_cmd` as an explicit `StringCommand` argument instead of an `f"{docker_cmd} ..."` prefix

**`pyinfra/operations/podman.py`** (commit `5cd24500`, new)
- Thin proxy module wrapping all 10 docker operations
- Each proxy sets `kwargs["docker_cmd"] = "podman"` (or `compose_command="podman compose"` for `compose`) and delegates via `docker.<op>._inner(...)`
- Docstrings document each as a proxy around the equivalent Docker operation

**`pyinfra/facts/docker.py`** (commit `580735d4`)
- Added `_docker_cmd(kwargs)` helper — replaced 10 identical `kwargs.get("docker_cmd") or "docker"` extractions (3 `requires_command` + 7 `command` sites)
- Added `_docker_inspect_all(docker_cmd, resource, list_command)` helper — replaced 3 identical inspect-all command templates (containers `ps -qa`, images `images -q`, plugins `plugin ls -q`)
- `DockerSystemInfo.command()` now respects `docker_cmd`

**`pyinfra/facts/podman.py`** (commit `8a7fe138`)
- Fixed `PodmanFactBase` docstring (was an unfinished fragment)
- Updated `PodmanSystemInfo` and `PodmanPs` docstrings to match the Docker ``Returns ...`` convention

**`pyinfra-metadata.toml`** (commit `5cd24500`)
- Registered `podman-ops` plugin (`name="podman"`, `path="src/pyinfra/operations/podman.py"`, `type="operation"`, `tags=["containers"]`)

**Tests** (commit `9a3307be`)
- Added `docker_cmd="podman"` fixtures for `login`/`logout` (4 fixtures)
- Added `docker_cmd="podman"` fixture for `build` (`build_with_docker_cmd.json`)
- Added 10 podman proxy operation fixture directories (`podman.container`, `podman.image`, `podman.build`, `podman.volume`, `podman.network`, `podman.plugin`, `podman.login`, `podman.logout`, `podman.prune`, `podman.compose`)
- Added `DockerSystemInfo` fact fixtures (default + `docker_cmd=podman`)
- Updated 63 existing Docker operation fixtures to include `docker_cmd=docker` in fact keys

**Documentation**
- Regenerated `docs/operations/docker.md` and `docs/operations/podman.md` via `scripts/generate_operations_docs.py`

### Commit organization

6 atomic commits (in order):

| Commit | Type | Scope | What |
|---|---|---|---|
| `580735d4` | `refactor(facts.docker)` | add `docker_cmd` helpers | dedup 10 `kwargs.get("docker_cmd") or "docker"` extractions + 3 inspect-all templates; `DockerSystemInfo.command()` now respects `docker_cmd` |
| `8a7fe138` | `docs(facts.podman)` | fix incomplete docstrings | complete `PodmanFactBase` fragment; update `PodmanSystemInfo`/`PodmanPs` |
| `9fffb567` | `feat(operations.docker)` | add `docker_cmd` parameter | thread `docker_cmd` through all 10 docker operations |
| `bf67c22e` | `refactor(operations.docker.util)` | split f-strings into explicit `StringCommand` args | 16 command builders use `StringCommand(docker_cmd, "subcommand", ...)` |
| `5cd24500` | `feat(operations)` | add `podman` proxy operations | new `operations/podman.py` + `podman-ops` metadata plugin |
| `9a3307be` | `test` | add `docker_cmd` and podman fixtures | 80 test files: 63 updated + 17 new fixture files |

### Verification

- `uv run pytest tests/test_operations.py tests/test_facts.py` → 1428 passed
- `uv run ruff check` → pass (only pre-existing E402 on `docker.py:22` from base commit)
- `uv run ruff format --check` → pass
- `uv run mypy` → pass

### Checklist

- [x] Pull request is based on the default branch (`3.x` at this time)
- [x] Pull request includes tests for any new/updated operations/facts
- [x] Pull request includes documentation for any new/updated operations/facts
- [x] Tests pass (see `scripts/dev-test.sh`)
- [x] Type checking & code style passes (see `scripts/dev-lint.sh`)
- [x] Pull request title follows the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) format (`feat(operations.docker): allow podman to replace docker via docker_cmd`)
- [x] Commit scope follows allowed scopes (`operations.docker`)

### Notes for reviewers

- `DockerAuths` fact intentionally does **not** accept `docker_cmd` — it reads `${DOCKER_CONFIG:-$HOME/.docker}/config.json` directly, which is shared between docker and podman (both honor `DOCKER_CONFIG` and default to `~/.docker/config.json`).
- `compose` keeps its own `compose_command: str = "docker compose"` default (with space) since `docker compose`/`podman compose` is a subcommand invocation, not a bare binary name.
- `login`/`logout` hardcode neither `docker` nor `podman` in generated commands; `docker_cmd` controls the binary. Prose in the `login` docstring no longer says ``docker login``.
- Podman facts (`facts/podman.py`) remain standalone; they do not proxy to Docker facts because the fact framework lacks the `_inner` escape hatch that operations use.
