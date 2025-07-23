import re
import subprocess
from typing import Callable

import pytest
import testinfra.host


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

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8")
        if isinstance(stderr, bytes):
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

    @staticmethod
    def run_container_test_host(
        container: str,
        cmd: str,
        callback: Callable[[testinfra.host.Host], None],
    ) -> None:
        stdout, _ = Helpers.run(
            f"docker run -d {container} tail -f /dev/null",
        )
        cid = stdout.strip()

        try:
            Helpers.run_check_output(
                f"pyinfra -y @docker/{cid} {cmd}",
                expected_lines=["docker build complete"],
            )

            host = testinfra.get_host(f"docker://{cid}")
            callback(host)
        finally:
            Helpers.run(f"docker rm -f {cid}")


@pytest.fixture(scope="module")
def helpers():
    return Helpers
