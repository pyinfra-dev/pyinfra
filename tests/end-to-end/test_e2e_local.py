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
