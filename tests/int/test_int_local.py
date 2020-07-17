from shutil import rmtree
from tempfile import mkdtemp

import pytest


@pytest.mark.int
@pytest.mark.local
def test_int_local_file_no_changes(helpers):
    temp_dir = mkdtemp()

    try:
        helpers.run(  # first run = create the file
            'pyinfra -v @local files.file _testfile',
            expected_lines=['@local] Success'],
            cwd=temp_dir,
        )

        helpers.run(  # second run = no changes
            'pyinfra -v @local files.file _testfile',
            expected_lines=['@local] No changes'],
            cwd=temp_dir,
        )
    finally:
        rmtree(temp_dir)


@pytest.mark.int
@pytest.mark.local
def test_int_local_directory_no_changes(helpers):
    temp_dir = mkdtemp()

    try:
        helpers.run(  # first run = create the directory
            'pyinfra -v @local files.directory _testdir',
            expected_lines=['@local] Success'],
            cwd=temp_dir,
        )

        helpers.run(  # second run = no changes
            'pyinfra -v @local files.directory _testdir',
            expected_lines=['@local] No changes'],
            cwd=temp_dir,
        )

        helpers.run(  # third run (remove) = remove directory
            'pyinfra -v @local files.directory _testdir present=False',
            expected_lines=['@local] Success'],
            cwd=temp_dir,
        )

        helpers.run(  # fourth run (remove) = no chances
            'pyinfra -v @local files.directory _testdir present=False',
            expected_lines=['@local] No changes'],
            cwd=temp_dir,
        )
    finally:
        rmtree(temp_dir)


@pytest.mark.int
@pytest.mark.local
def test_int_local_link_no_changes(helpers):
    temp_dir = mkdtemp()

    try:
        helpers.run(  # first run = create the link
            'pyinfra -v @local files.link _testlink target=_testfile',
            expected_lines=['@local] Success'],
            cwd=temp_dir,
        )

        helpers.run(  # second run = no changes
            'pyinfra -v @local files.link _testlink target=_testfile',
            expected_lines=['@local] No changes'],
            cwd=temp_dir,
        )
    finally:
        rmtree(temp_dir)


@pytest.mark.int
@pytest.mark.local
def test_int_local_line_no_changes(helpers):
    temp_dir = mkdtemp()

    try:
        helpers.run(  # first run = create the line
            'pyinfra -v @local files.line _testfile someline',
            expected_lines=['@local] Success'],
            cwd=temp_dir,
        )

        helpers.run(  # second run = no changes
            'pyinfra -v @local files.line _testfile someline',
            expected_lines=['@local] No changes'],
            cwd=temp_dir,
        )

        helpers.run(  # replace the line
            'pyinfra -v @local files.line _testfile someline replace=anotherline',
            expected_lines=['@local] Success'],
            cwd=temp_dir,
        )

        helpers.run(  # second run replace the line = no changes
            'pyinfra -v @local files.line _testfile someline replace=anotherline',
            expected_lines=['@local] No changes'],
            cwd=temp_dir,
        )
    finally:
        rmtree(temp_dir)
