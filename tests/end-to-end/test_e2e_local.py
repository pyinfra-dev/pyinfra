"""
Local integration tests - mostly checking for idempotency on file operations.
"""

from shutil import rmtree
from tempfile import mkdtemp

import pytest


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
        "pyinfra -v @local files.file _testfile",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run = no changes
        "pyinfra -v @local files.file _testfile",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_directory_no_changes(helpers, temp_dir):
    helpers.run_check_output(  # first run = create the directory
        "pyinfra -v @local files.directory _testdir",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run = no changes
        "pyinfra -v @local files.directory _testdir",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # third run (remove) = remove directory
        "pyinfra -v @local files.directory _testdir present=False",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # fourth run (remove) = no chances
        "pyinfra -v @local files.directory _testdir present=False",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_link_no_changes(helpers, temp_dir):
    helpers.run_check_output(  # first run = create the link
        "pyinfra -v @local files.link _testlink target=_testfile",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run = no changes
        "pyinfra -v @local files.link _testlink target=_testfile",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_line_no_changes(helpers, temp_dir):
    helpers.run_check_output(  # first run = create the line
        "pyinfra -v @local files.line _testfile someline",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run = no changes
        "pyinfra -v @local files.line _testfile someline",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # replace the line
        "pyinfra -v @local files.line _testfile someline replace=anotherline",
        expected_lines=["@local] Success"],
        cwd=temp_dir,
    )

    helpers.run_check_output(  # second run replace the line = no changes
        "pyinfra -v @local files.line _testfile someline replace=anotherline",
        expected_lines=["@local] No changes"],
        cwd=temp_dir,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_pre_post_conditions(helpers):
    helpers.run_check_output(
        (
            "pyinfra -v @local server.shell uptime "
            "precondition='exit 0' "
            "postcondition='exit 0'"
        ),
        expected_lines=["@local] Success"],
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_failed_precondition(helpers):
    helpers.run_check_output(
        "pyinfra -v @local server.shell uptime precondition='exit 1'",
        expected_lines=["@local] Error: precondition failed: exit 1"],
        expected_exit_code=1,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_failed_postcondition(helpers):
    helpers.run_check_output(
        "pyinfra -v @local server.shell uptime postcondition='exit 1'",
        expected_lines=["@local] Error: postcondition failed: exit 1"],
        expected_exit_code=1,
    )


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_line_ensure_newline_true(helpers, tmp_path):
    path = tmp_path / "_testfile"

    path.write_bytes(b"hello world")
    helpers.run_check_output(
        "pyinfra -v @local files.line _testfile someline ensure_newline=true",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )
    assert path.read_bytes() == b"hello world\nsomeline\n"

    path.write_bytes(b"hello world\n")
    helpers.run_check_output(
        "pyinfra -v @local files.line _testfile someline ensure_newline=true",
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
        "pyinfra -v @local files.line _testfile someline ensure_newline=false",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )
    assert path.read_bytes() == b"hello worldsomeline\n"

    path.write_bytes(b"hello world\n")
    helpers.run_check_output(
        "pyinfra -v @local files.line _testfile someline ensure_newline=false",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )
    assert path.read_bytes() == b"hello world\nsomeline\n"
