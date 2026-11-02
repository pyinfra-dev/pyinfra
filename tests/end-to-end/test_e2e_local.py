"""
Local integration tests - mostly checking for idempotency on file operations.
"""

import os
import shlex
from io import StringIO
from shutil import rmtree
from tempfile import mkdtemp

import pytest
from pyinfra.api import Config, Inventory, State
from pyinfra.api.connect import connect_all


@pytest.fixture()
def temp_dir():
    temp_dir = mkdtemp()
    try:
        yield temp_dir
    finally:
        rmtree(temp_dir)


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_file_no_changes(helpers, temp_dir):
    helpers.run_check_output(  # first run = create the file
        "pyinfra -y -v @local files.file _testfile",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run = no changes
        "pyinfra -y -v @local files.file _testfile",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_directory_no_changes(helpers, temp_dir):
    helpers.run_check_output(  # first run = create the directory
        "pyinfra -y -v @local files.directory _testdir",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run = no changes
        "pyinfra -y -v @local files.directory _testdir",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # third run (remove) = remove directory
        "pyinfra -y -v @local files.directory _testdir present=False",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # fourth run (remove) = no chances
        "pyinfra -y -v @local files.directory _testdir present=False",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_link_no_changes(helpers, temp_dir):
    helpers.run_check_output(  # first run = create the link
        "pyinfra -y -v @local files.link _testlink target=_testfile",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run = no changes
        "pyinfra -y -v @local files.link _testlink target=_testfile",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_line_no_changes(helpers, temp_dir):
    helpers.run_check_output(  # first run = create the line
        "pyinfra -y -v @local files.line _testfile someline",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run = no changes
        "pyinfra -y -v @local files.line _testfile someline",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # replace the line
        "pyinfra -y -v @local files.line _testfile someline replace=anotherline",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run replace the line = no changes
        "pyinfra -y -v @local files.line _testfile someline replace=anotherline",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_line_ensure_newline_true(helpers, tmp_path):
    path = tmp_path / "_testfile"

    path.write_bytes(b"hello world")
    helpers.run_check_output(
        "pyinfra -y -v @local files.line _testfile someline ensure_newline=true",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )
    assert path.read_bytes() == b"hello world\nsomeline\n"

    path.write_bytes(b"hello world\n")
    helpers.run_check_output(
        "pyinfra -y -v @local files.line _testfile someline ensure_newline=true",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )
    assert path.read_bytes() == b"hello world\nsomeline\n"


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_line_ensure_newline_false(helpers, tmp_path):
    path = tmp_path / "_testfile"

    path.write_bytes(b"hello world")
    helpers.run_check_output(
        "pyinfra -y -v @local files.line _testfile someline ensure_newline=false",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )
    assert path.read_bytes() == b"hello worldsomeline\n"

    path.write_bytes(b"hello world\n")
    helpers.run_check_output(
        "pyinfra -y -v @local files.line _testfile someline ensure_newline=false",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )
    assert path.read_bytes() == b"hello world\nsomeline\n"


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_retry_resends_a_generator_stdin(helpers, tmp_path):
    dest = os.fspath(tmp_path / "out")
    marker = os.fspath(tmp_path / "marker")
    command = (
        f"cat > {shlex.quote(dest)}; "
        f"if [ -f {shlex.quote(marker)} ]; then exit 0; fi; "
        f"touch {shlex.quote(marker)}; exit 1"
    )
    (tmp_path / "deploy.py").write_text(
        "from pyinfra.operations import server\n\n"
        "server.shell(\n"
        f"    {command!r},\n"
        "    _stdin=(line for line in ['header', 'payload']),\n"
        "    _retries=1,\n"
        "    _retry_delay=0,\n"
        ")\n"
    )

    helpers.run_check_output(
        "pyinfra -y -v @local deploy.py",
        expected_lines=["@local] Success"],
        cwd=os.fspath(tmp_path),
    )

    # The first attempt consumes the generator; without buffering the retry truncates
    # the destination and writes nothing.
    assert (tmp_path / "out").read_text() == "header\npayload\n"


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_sudo_retry_resends_a_generator_stdin(helpers, tmp_path):
    dest = os.fspath(tmp_path / "out")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_sudo = bin_dir / "sudo"
    fake_sudo.write_text(
        "#!/bin/sh\n"
        'if [ -z "${SUDO_ASKPASS:-}" ]; then\n'
        '    echo "sudo: a password is required" >&2\n'
        "    exit 1\n"
        "fi\n"
        "while [ $# -gt 0 ]; do\n"
        '    case "$1" in\n'
        "        -H|-A|-k|-n) shift ;;\n"
        "        -u) shift 2 ;;\n"
        "        *) break ;;\n"
        "    esac\n"
        "done\n"
        'exec "$@"\n'
    )
    fake_sudo.chmod(0o755)

    (tmp_path / "deploy.py").write_text(
        "import os\n"
        "import pyinfra.connectors.util as util\n"
        "from pyinfra.operations import server\n\n"
        'util.getpass = lambda prompt: "PASSWORD"  # pragma: allowlist secret\n'
        f"os.environ['PATH'] = {os.fspath(bin_dir)!r} + os.pathsep + os.environ['PATH']\n\n"
        "server.shell(\n"
        f"    {f'cat > {shlex.quote(dest)}'!r},\n"
        "    _stdin=(line for line in ['header', 'payload']),\n"
        "    _sudo=True,\n"
        ")\n"
    )

    helpers.run_check_output(
        "pyinfra -y -v @local deploy.py",
        expected_lines=["@local] Success"],
        cwd=os.fspath(tmp_path),
    )

    assert (tmp_path / "out").read_text() == "header\npayload\n"


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_get_file_invalid_utf8_keeps_stringio_intact(tmp_path):
    source = tmp_path / "binary"
    source.write_bytes(b"\xffnot-utf8")

    inventory = Inventory(([("@local", {})], {}), override_data={})
    state = State(inventory, Config())
    connect_all(state)
    host = inventory.get_host("@local")

    destination = StringIO("stale")
    with pytest.raises(UnicodeDecodeError):
        host.get_file(os.fspath(source), destination)

    # The decode failure must not erase the destination first.
    assert destination.getvalue() == "stale"
