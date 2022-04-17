import re
import subprocess

import pytest


class Helpers:
    @staticmethod
    def run(command, cwd=None, expected_exit_code=0):
        results = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )

        stdout, stderr = results.communicate()

        if type(stdout) is bytes:
            stdout = stdout.decode("utf-8")
        if type(stderr) is bytes:
            stderr = stderr.decode("utf-8")

        assert results.returncode == expected_exit_code, stderr

        return stdout, stderr

    @staticmethod
    def run_check_output(command, expected_lines=None, **kwargs):
        if expected_lines is None:
            expected_lines = ["Connected", "Starting operation", "Errors: 0"]

        _, stderr = Helpers.run(command, **kwargs)

        for line in expected_lines:
            assert re.search(line, stderr, re.MULTILINE), 'Line "{0}" not found in output!'.format(
                line,
            )


@pytest.fixture(scope="module")
def helpers():
    return Helpers
