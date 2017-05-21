# pyinfra
# File: tests/test_cli.py
# Desc: tests for the pyinfra CLI

from collections import defaultdict
from unittest import TestCase

import six

from click.testing import CliRunner

from pyinfra_cli.exceptions import CliError
from pyinfra_cli.legacy import setup_arguments
from pyinfra_cli.main import cli


class TestCliExceptions(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_cli = CliRunner()
        cls.old_cli_show = CliError.show

    @classmethod
    def tearDownClass(cls):
        CliError.show = cls.old_cli_show

    def setUp(self):
        self.exception = None
        CliError.show = lambda e: self.capture_cli_error(e)

    def capture_cli_error(self, e):
        self.exception = e
        self.old_cli_show()

    def assert_cli_exception(self, args, message):
        self.test_cli.invoke(cli, args)

        self.assertIsInstance(self.exception, CliError)
        self.assertEqual(self.exception.message, message)

    def test_bad_inventory_file(self):
        self.assert_cli_exception(
            ['thing/nop.py', 'fact', 'os'],
            'No inventory file: thing/nop.py',
        )

    def test_bad_deploy_file(self):
        self.assert_cli_exception(
            ['example/inventories/dev.py', 'example/deploy.py', 'nop.py'],
            'No deploy file: nop.py',
        )

    def test_bad_fact(self):
        self.assert_cli_exception(
            ['example/inventories/dev.py', 'fact', 'thing'],
            'No fact: thing',
        )


class TestLegacyCliArguments(TestCase):
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
            CliError, message='string is not a valid integer for --parallel',
        ):
            self.assert_valid_arguments({
                '--parallel': 'string',
            })

    def test_invalid_files(self):
        with self.assertRaises(CliError, message='Deploy file not found: nop.py'):
            self.assert_valid_arguments({
                'DEPLOY': 'nop.py',
            })

        with self.assertRaises(
            CliError, message='Private key file not found: nop.key',
        ):
            self.assert_valid_arguments({
                '--key': 'nop.key',
            })
