# pyinfra
# File: tests/test_cli.py
# Desc: tests for the pyinfra CLI

from collections import defaultdict
from datetime import datetime
from os import path
from random import shuffle
from unittest import TestCase

import six

from click.testing import CliRunner
from six.moves import cStringIO as StringIO

import pyinfra

from pyinfra import pseudo_state
from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.modules import server
from pyinfra_cli.exceptions import CliError
from pyinfra_cli.legacy import setup_arguments
from pyinfra_cli.main import cli
from pyinfra_cli.util import get_operation_and_args, json_encode, load_deploy_file

from .paramiko_util import PatchSSHTestCase
from .util import make_inventory


class TestCliDeployOperations(PatchSSHTestCase):
    def test_deploy(self):
        # Run 10 iterations of the test - each time shuffling the order of the
        # hosts - ensuring that the ordering has no effect on the operation order.
        for _ in range(10):
            self._do_test_deploy()

    def _do_test_deploy(self):
        correct_op_name_and_host_names = [
            ('First main operation', True),  # true for all hosts
            ('Second main operation', ('somehost',)),
            ('tests/test_deploy/a_task.py | First task operation', ('anotherhost',)),
            ('tests/test_deploy/a_task.py | Second task operation', ('anotherhost',)),
            ('tests/test_deploy/a_task.py | First task operation', True),
            ('tests/test_deploy/a_task.py | Second task operation', True),
            ('Loop-0 main operation', True),
            ('Loop-1 main operation', True),
            ('Third main operation', True),
        ]

        hosts = ['somehost', 'anotherhost', 'someotherhost']
        shuffle(hosts)

        inventory = make_inventory(hosts=hosts)
        state = State(inventory, Config())
        state.deploy_dir = path.join('tests', 'test_deploy')

        connect_all(state)
        pseudo_state.set(state)

        pyinfra.is_cli = True
        load_deploy_file(state, path.join(state.deploy_dir, 'deploy.py'))
        pyinfra.is_cli = False

        op_order = state.get_op_order()

        for i, (correct_op_name, correct_host_names) in enumerate(
            correct_op_name_and_host_names,
        ):
            op_hash = op_order[i]
            op_meta = state.op_meta[op_hash]

            self.assertEqual(list(op_meta['names'])[0], correct_op_name)

            for host in inventory:
                op_hashes = state.meta[host]['op_hashes']
                if correct_host_names is True or host.name in correct_host_names:
                    self.assertIn(op_hash, op_hashes)
                else:
                    self.assertNotIn(op_hash, op_hashes)


class TestCliUtil(TestCase):
    def test_json_encode_function(self):
        self.assertEqual(
            json_encode(setup_arguments),
            'setup_arguments',
        )

    def test_json_encode_datetime(self):
        now = datetime.utcnow()

        self.assertEqual(
            json_encode(now),
            now.isoformat(),
        )

    def test_json_encode_file(self):
        file = StringIO()

        self.assertEqual(
            json_encode(file),
            'In memory file: ',
        )

    def test_json_encode_set(self):
        self.assertEqual(
            json_encode({1, 2, 3}),
            [1, 2, 3],
        )

    def test_setup_no_module(self):
        with self.assertRaises(CliError) as context:
            get_operation_and_args(('no.op',))

        self.assertEqual(
            context.exception.message,
            'No such module: no',
        )

    def test_setup_no_op(self):
        with self.assertRaises(CliError) as context:
            get_operation_and_args(('server.no',))

        self.assertEqual(
            context.exception.message,
            'No such operation: server.no',
        )

    def test_setup_op_and_args(self):
        commands = ('server.user', 'one', 'two', 'hello=world')

        self.assertEqual(
            get_operation_and_args(commands),
            (
                server.user,
                (['one', 'two'], {'hello': 'world'}),
            ),
        )

    def test_setup_op_and_json_args(self):
        commands = ('server.user', '[["one", "two"], {"hello": "world"}]')

        self.assertEqual(
            get_operation_and_args(commands),
            (
                server.user,
                (['one', 'two'], {'hello': 'world'}),
            ),
        )


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

    def test_bad_deploy_file(self):
        self.assert_cli_exception(
            ['my-server.net', 'nop.py'],
            'No deploy file: nop.py',
        )

    def test_bad_fact(self):
        self.assert_cli_exception(
            ['my-server.net', 'fact', 'thing'],
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
