from unittest.mock import patch

from pyinfra.context import ctx_host, ctx_state
from pyinfra.facts.files import FileContents
from pyinfra.operations import files
from pyinfra_testing.util import FakeState, create_host


def _put_with_diff(src_path, dest, current_contents):
    state = FakeState()
    state.config.DIFF = True
    host = create_host(
        state,
        facts={
            "files.File": {f"path={dest}": {"mode": 644, "user": "root", "group": "root"}},
            "files.Sha1File": {f"path={dest}": "different"},
            "files.Directory": {f"path={dest.rsplit('/', 1)[0]}": True},
            "files.FileContents": {f"path={dest}": current_contents},
        },
    )
    requested_facts = []
    real_get_fact = host.get_fact

    def get_fact(fact_cls, *args, **kwargs):
        requested_facts.append(fact_cls)
        return real_get_fact(fact_cls, *args, **kwargs)

    with (
        ctx_state.use(state),
        ctx_host.use(host),
        patch.object(host, "get_fact", get_fact),
        patch.object(host, "log", lambda message, log_func: None, create=True),
        patch("pyinfra.operations.files.logger") as logger,
    ):
        commands = list(files.put._inner(str(src_path), dest))

    logged = "\n".join(str(call) for call in logger.info.call_args_list)
    return commands, requested_facts, logged


def test_put_diff_binary_source_does_not_fetch_remote_contents(tmp_path):
    src = tmp_path / "some-binary"
    src.write_bytes(b"\x81\x8d\x8f\x90\x9d")

    commands, requested_facts, logged = _put_with_diff(src, "/opt/bin/some-binary", [])

    assert len(commands) == 1
    assert FileContents not in requested_facts
    assert "Binary file modified" in logged


def test_put_diff_text_source_shows_a_diff(tmp_path):
    src = tmp_path / "some-text"
    src.write_text("new line\n")

    commands, requested_facts, logged = _put_with_diff(src, "/opt/some-text", ["old line"])

    assert len(commands) == 1
    assert FileContents in requested_facts
    assert "old line" in logged and "new line" in logged
