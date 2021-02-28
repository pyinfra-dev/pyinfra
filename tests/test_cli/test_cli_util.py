import os
import sys
from datetime import datetime
from unittest import TestCase

import pytest
from six.moves import cStringIO as StringIO

from pyinfra.operations import server
from pyinfra_cli.exceptions import CliError
from pyinfra_cli.util import get_operation_and_args, json_encode


class TestCliUtil(TestCase):
    def test_json_encode_function(self):
        assert json_encode(get_operation_and_args) == 'Function: get_operation_and_args'

    def test_json_encode_datetime(self):
        now = datetime.utcnow()
        assert json_encode(now) == now.isoformat()

    def test_json_encode_file(self):
        file = StringIO()
        assert json_encode(file) == 'In memory file: '

    def test_json_encode_set(self):
        assert json_encode({1, 2, 3}) == [1, 2, 3]

    def test_setup_no_module(self):
        with self.assertRaises(CliError) as context:
            get_operation_and_args(('no.op',))
        assert context.exception.message == 'No such module: no'

    def test_setup_no_op(self):
        with self.assertRaises(CliError) as context:
            get_operation_and_args(('server.no',))

        assert context.exception.message == 'No such operation: server.no'

    def test_setup_op_and_args(self):
        commands = ('server.user', 'one', 'two', 'hello=world')

        assert get_operation_and_args(commands) == (
            server.user,
            (['one', 'two'], {'hello': 'world'}),
        )

    def test_setup_op_and_json_args(self):
        commands = ('server.user', '[["one", "two"], {"hello": "world"}]')

        assert get_operation_and_args(commands) == (
            server.user,
            (['one', 'two'], {'hello': 'world'}),
        )


@pytest.fixture(scope='function')
def user_sys_path():
    user_pkg = os.path.dirname(__file__) + '/user'
    sys.path.append(user_pkg)
    yield None
    sys.path.pop()
    to_rm = []
    for k, v in sys.modules.items():
        v = getattr(v, '__file__', '')
        if isinstance(v, str) and v.startswith(user_pkg):
            to_rm.append(k)
    for k in to_rm:
        del sys.modules[k]


# def test_no_user_op():
#     commands = ('test_ops.dummy_op', 'arg1', 'arg2')
#     with pytest.raises(CliError, match='^No such module: test_ops$'):
#         get_operation_and_args(commands)


def test_user_op(user_sys_path):
    commands = ('test_ops.dummy_op', 'arg1', 'arg2')
    res = get_operation_and_args(commands)

    import test_ops
    assert res == (test_ops.dummy_op, (['arg1', 'arg2'], {}))
