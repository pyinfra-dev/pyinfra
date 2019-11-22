from datetime import datetime
from unittest import TestCase

from six.moves import cStringIO as StringIO

from pyinfra.modules import server
from pyinfra_cli.exceptions import CliError
from pyinfra_cli.util import get_operation_and_args, json_encode


class TestCliUtil(TestCase):
    def test_json_encode_function(self):
        self.assertEqual(
            json_encode(get_operation_and_args),
            'get_operation_and_args',
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
