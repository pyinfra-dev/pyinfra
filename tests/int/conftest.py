import re
import subprocess

import pytest


class Helpers:
    @staticmethod
    def run(command, expected_lines=None, cwd='examples'):
        if expected_lines is None:
            expected_lines = ['Connected', 'Starting operation', 'Errors: 0']

        results = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )

        stdout, stderr = results.communicate()

        if type(stdout) is bytes:
            stdout = stdout.decode('utf-8')
        if type(stderr) is bytes:
            stderr = stderr.decode('utf-8')

        assert results.returncode == 0, stderr

        for line in expected_lines:
            assert re.search(line, stderr, re.MULTILINE)


@pytest.fixture
def helpers():
    return Helpers
