from collections import defaultdict
from unittest import TestCase

import six

from pyinfra.modules import server
from pyinfra_cli.exceptions import CliError
from pyinfra_cli.legacy import setup_arguments
from pyinfra_cli.util import get_operation_and_args


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
            CliError, msg='string is not a valid integer for --parallel',
        ):
            self.assert_valid_arguments({
                '--parallel': 'string',
            })

    def test_invalid_files(self):
        with self.assertRaises(CliError, msg='Deploy file not found: nop.py'):
            self.assert_valid_arguments({
                'DEPLOY': 'nop.py',
            })

        with self.assertRaises(
            CliError, msg='Private key file not found: nop.key',
        ):
            self.assert_valid_arguments({
                '--key': 'nop.key',
            })

    def test_legacy_setup_op_and_args(self):
        op_string = 'server.user'
        args_string = 'one,two,hello=world'

        self.assertEqual(
            get_operation_and_args((op_string, args_string)),
            (
                server.user,
                (['one', 'two'], {'hello': 'world'}),
            ),
        )

    def test_legacy_setup_op_and_args_list(self):
        op_string = 'server.user'
        args_string = '[one,two],hello=world'

        self.assertEqual(
            get_operation_and_args((op_string, args_string)),
            (
                server.user,
                ([['one', 'two']], {'hello': 'world'}),
            ),
        )

    def test_legacy_setup_op_and_json_args(self):
        op_string = 'server.user'
        args_string = '[["one", "two"], {"hello": "world"}]'

        self.assertEqual(
            get_operation_and_args((op_string, args_string)),
            (
                server.user,
                (['one', 'two'], {'hello': 'world'}),
            ),
        )
