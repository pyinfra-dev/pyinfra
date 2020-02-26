'''Common pytest integration code.'''
import re
import subprocess

import pytest


class Helpers:
    @staticmethod
    def run(command, expected_stdout_lines=None, expected_stderr_lines=None,
            cwd='examples'):
        '''Helper function to eliminate pytest code.'''
        if expected_stdout_lines is None:
            expected_stdout_lines = ['Connected', 'Starting operation', 'Errors: 0']
        if expected_stderr_lines is None:
            expected_stderr_lines = ['']
        results = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=cwd)
        stdout, stderr = results.communicate()
        if type(stdout) is bytes:
            stdout = stdout.decode('utf-8')
        if type(stderr) is bytes:
            stderr = stderr.decode('utf-8')
        assert results.returncode == 0
        for line in expected_stdout_lines:
            print(line)
            assert re.search(line, stdout, re.MULTILINE)
        for line in expected_stderr_lines:
            print(line)
            assert re.search(line, stderr, re.MULTILINE)


@pytest.fixture
def helpers():
    '''Helper functions for testing.'''
    return Helpers
