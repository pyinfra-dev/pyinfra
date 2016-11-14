# pyinfra
# File: tests/test_api.py
# Desc: tests for the pyinfra API

from collections import defaultdict
from unittest import TestCase

import six

from pyinfra.cli import CliError, setup_arguments
from pyinfra.modules import server


class DefaultNoneDict():
    pass


class TestCliArguments(TestCase):
    def make_cli_arguments(self, arguments):
        default_arguments = defaultdict(lambda: None)
        default_arguments.update(arguments)

        return default_arguments

    def assert_valid_arguments(self, arguments, check_arguments=None):
        arguments = self.make_cli_arguments(arguments)
        parsed_arguments = setup_arguments(arguments)

        if check_arguments:
            for key, value in six.iteritems(check_arguments):
                self.assertEqual(parsed_arguments[key], value)

    def test_int_arguments(self):
        self.assert_valid_arguments({
            '--parallel': '5',
            '--port': '22',
            '--fail-percent': '30',
        }, {
            'parallel': 5,
            'port': 22,
            'fail_percent': 30,
        })

    def test_wrong_int_argument(self):
        with self.assertRaises(
            CliError, message='string is not a valid integer for --parallel'
        ):
            self.assert_valid_arguments({
                '--parallel': 'string',
            })

    def test_op_and_args(self):
        self.assert_valid_arguments({
            '--run': 'server.user',
            'ARGS': 'ignore_errors=true',
        }, {
            'op': server.user,
            'op_args': ([], {'ignore_errors': True})
        })

    def test_default_op(self):
        self.assert_valid_arguments({
            '--run': 'echo hi!',
        }, {
            'op': server.shell,
            'op_args': (['echo hi!'], {}),
        })

    def test_invalid_op(self):
        with self.assertRaises(CliError, message='Invalid operation: thisisnotanop'):
            self.assert_valid_arguments({
                '--run': 'thisisnotanop',
                'ARGS': 'args',
            })

        with self.assertRaises(CliError, message='No such module: nomodule'):
            self.assert_valid_arguments({
                '--run': 'nomodule.op',
            })

        with self.assertRaises(CliError, message='No such operation: noop'):
            self.assert_valid_arguments({
                '--run': 'server.noop',
            })

    def test_fact(self):
        self.assert_valid_arguments({
            '--fact': 'linux_distribution',
        }, {
            'fact': 'linux_distribution',
        })

    def test_fact_with_args(self):
        self.assert_valid_arguments({
            '--fact': 'file:/file.txt',
        }, {
            'fact': 'file',
            'fact_args': ['/file.txt'],
        })

    def test_invalid_fact(self):
        with self.assertRaises(CliError, message='Invalid fact: thisisnotafact'):
            self.assert_valid_arguments({
                '--fact': 'thisisnotafact',
            })

    def test_invalid_files(self):
        with self.assertRaises(CliError, message='Deploy file not found: nop.py'):
            self.assert_valid_arguments({
                'DEPLOY': 'nop.py',
            })

        with self.assertRaises(
            CliError, message='Private key file not found: nop.key'
        ):
            self.assert_valid_arguments({
                '--key': 'nop.key',
            })
