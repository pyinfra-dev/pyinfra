from collections import defaultdict
from inspect import currentframe, getframeinfo
from os import path
from unittest import TestCase

from mock import mock_open, patch

import pyinfra

from pyinfra import pseudo_host, pseudo_state
from pyinfra.api import (
    BaseStateCallback,
    Config,
    FileDownloadCommand,
    FileUploadCommand,
    OperationError,
    OperationValueError,
    State,
    StringCommand,
)
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.operation import add_op, get_operation_names, OperationMeta
from pyinfra.api.operations import run_ops
from pyinfra.operations import files, python, server

from ..paramiko_util import (
    FakeBuffer,
    FakeChannel,
    PatchSSHTestCase,
)
from ..util import FakeState, make_inventory


class TestOperationMeta(TestCase):
    def test_get_operation_names(self):
        assert len(get_operation_names()) > 0

    def test_operation_meta_repr(self):
        op_meta = OperationMeta('hash', [])
        assert repr(op_meta) == 'commands:[] changed:False hash:hash'


class TestOperationsApi(PatchSSHTestCase):
    def test_op(self):
        inventory = make_inventory()
        somehost = inventory.get_host('somehost')
        anotherhost = inventory.get_host('anotherhost')

        state = State(inventory, Config())
        state.add_callback_handler(BaseStateCallback())

        # Enable printing on this test to catch any exceptions in the formatting
        state.print_output = True
        state.print_input = True
        state.print_fact_info = True
        state.print_noop_info = True

        connect_all(state)

        add_op(
            state, files.file,
            '/var/log/pyinfra.log',
            user='pyinfra',
            group='pyinfra',
            mode='644',
            create_remote_dir=False,
            sudo=True,
            sudo_user='test_sudo',
            su_user='test_su',
            ignore_errors=True,
            env={
                'TEST': 'what',
            },
        )

        op_order = state.get_op_order()

        # Ensure we have an op
        assert len(op_order) == 1

        first_op_hash = op_order[0]

        # Ensure the op name
        assert state.op_meta[first_op_hash]['names'] == {'Files/File'}

        # Ensure the commands
        assert state.ops[somehost][first_op_hash]['commands'] == [
            StringCommand('touch /var/log/pyinfra.log'),
            StringCommand('chmod 644 /var/log/pyinfra.log'),
            StringCommand('chown pyinfra:pyinfra /var/log/pyinfra.log'),
        ]

        # Ensure the global kwargs (same for both hosts)
        somehost_global_kwargs = state.ops[somehost][first_op_hash]['global_kwargs']
        assert somehost_global_kwargs['sudo'] is True
        assert somehost_global_kwargs['sudo_user'] == 'test_sudo'
        assert somehost_global_kwargs['su_user'] == 'test_su'
        assert somehost_global_kwargs['ignore_errors'] is True

        anotherhost_global_kwargs = state.ops[anotherhost][first_op_hash]['global_kwargs']
        assert anotherhost_global_kwargs['sudo'] is True
        assert anotherhost_global_kwargs['sudo_user'] == 'test_sudo'
        assert anotherhost_global_kwargs['su_user'] == 'test_su'
        assert anotherhost_global_kwargs['ignore_errors'] is True

        # Ensure run ops works
        run_ops(state)

        # Ensure ops completed OK
        assert state.results[somehost]['success_ops'] == 1
        assert state.results[somehost]['ops'] == 1
        assert state.results[anotherhost]['success_ops'] == 1
        assert state.results[anotherhost]['ops'] == 1

        # And w/o errors
        assert state.results[somehost]['error_ops'] == 0
        assert state.results[anotherhost]['error_ops'] == 0

        # And with the different modes
        run_ops(state, serial=True)
        run_ops(state, no_wait=True)

        disconnect_all(state)

    def test_op_call_direct_falls(self):
        inventory = make_inventory()
        somehost = inventory.get_host('somehost')
        state = State(inventory, Config())

        # Enable printing on this test to catch any exceptions in the formatting
        state.print_output = True
        state.print_input = True
        state.print_fact_info = True
        state.print_noop_info = True

        connect_all(state)

        with self.assertRaises(PyinfraError) as context:
            server.shell(state=state, host=somehost, commands='echo hi')

        assert context.exception.args[0] == (
            'Operation order number not provided in API mode - '
            'you must use `add_op` to add operations.'
        )

    def test_file_upload_op(self):
        inventory = make_inventory()

        state = State(inventory, Config())
        connect_all(state)

        with patch('pyinfra.operations.files.os_path.isfile', lambda *args, **kwargs: True):
            # Test normal
            add_op(
                state, files.put,
                name='First op name',
                src='files/file.txt',
                dest='/home/vagrant/file.txt',
            )

            # And with sudo
            add_op(
                state, files.put,
                src='files/file.txt',
                dest='/home/vagrant/file.txt',
                sudo=True,
                sudo_user='pyinfra',
            )

            # And with su
            add_op(
                state, files.put,
                src='files/file.txt',
                dest='/home/vagrant/file.txt',
                sudo=True,
                su_user='pyinfra',
            )

        op_order = state.get_op_order()

        # Ensure we have all ops
        assert len(op_order) == 3

        first_op_hash = op_order[0]
        second_op_hash = op_order[1]

        # Ensure first op is the right one
        assert state.op_meta[first_op_hash]['names'] == {'First op name'}

        somehost = inventory.get_host('somehost')
        anotherhost = inventory.get_host('anotherhost')

        # Ensure first op has the right (upload) command
        assert state.ops[somehost][first_op_hash]['commands'] == [
            StringCommand('mkdir -p /home/vagrant'),
            FileUploadCommand('files/file.txt', '/home/vagrant/file.txt'),
        ]

        # Ensure second op has sudo/sudo_user
        assert state.ops[somehost][second_op_hash]['global_kwargs']['sudo'] is True
        assert state.ops[somehost][second_op_hash]['global_kwargs']['sudo_user'] == 'pyinfra'

        # Ensure third has su_user
        assert state.ops[somehost][op_order[2]]['global_kwargs']['su_user'] == 'pyinfra'

        # Check run ops works
        with patch('pyinfra.api.util.open', mock_open(read_data='test!'), create=True):
            run_ops(state)

        # Ensure ops completed OK
        assert state.results[somehost]['success_ops'] == 3
        assert state.results[somehost]['ops'] == 3
        assert state.results[anotherhost]['success_ops'] == 3
        assert state.results[anotherhost]['ops'] == 3

        # And w/o errors
        assert state.results[somehost]['error_ops'] == 0
        assert state.results[anotherhost]['error_ops'] == 0

    def test_file_download_op(self):
        inventory = make_inventory()

        state = State(inventory, Config())
        connect_all(state)

        with patch('pyinfra.operations.files.os_path.isfile', lambda *args, **kwargs: True):
            add_op(
                state, files.get,
                name='First op name',
                src='/home/vagrant/file.txt',
                dest='files/file.txt',
            )

        op_order = state.get_op_order()

        assert len(op_order) == 1

        first_op_hash = op_order[0]
        assert state.op_meta[first_op_hash]['names'] == {'First op name'}

        somehost = inventory.get_host('somehost')
        anotherhost = inventory.get_host('anotherhost')

        # Ensure first op has the right (upload) command
        assert state.ops[somehost][first_op_hash]['commands'] == [
            FileDownloadCommand('/home/vagrant/file.txt', 'files/file.txt'),
        ]

        with patch('pyinfra.api.util.open', mock_open(read_data='test!'), create=True):
            run_ops(state)

        assert state.results[somehost]['success_ops'] == 1
        assert state.results[somehost]['ops'] == 1
        assert state.results[anotherhost]['success_ops'] == 1
        assert state.results[anotherhost]['ops'] == 1
        assert state.results[somehost]['error_ops'] == 0
        assert state.results[anotherhost]['error_ops'] == 0

    def test_function_call_op(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        is_called = []

        def mocked_function(*args, **kwargs):
            is_called.append(True)
            return None

        # Add op to both hosts
        add_op(state, python.call, mocked_function)

        # Ensure there is one op
        assert len(state.get_op_order()) == 1

        run_ops(state)

        assert is_called

    def test_run_once_serial_op(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        # Add a run once op
        add_op(state, server.shell, 'echo "hi"', run_once=True, serial=True)

        # Ensure it's added to op_order
        assert len(state.get_op_order()) == 1

        somehost = inventory.get_host('somehost')
        anotherhost = inventory.get_host('anotherhost')

        # Ensure between the two hosts we only run the one op
        assert len(state.ops[somehost]) + len(state.ops[anotherhost]) == 1

        # Check run works
        run_ops(state)

        assert (
            state.results[somehost]['success_ops']
            + state.results[anotherhost]['success_ops']
        ) == 1

    def test_rsync_op(self):
        inventory = make_inventory(hosts=('somehost',))
        state = State(inventory, Config())
        connect_all(state)

        with patch('pyinfra.api.connectors.ssh.check_can_rsync'):
            add_op(state, files.rsync, 'src', 'dest', sudo=True, sudo_user='root')

        assert len(state.get_op_order()) == 1

        with patch('pyinfra.api.connectors.ssh.run_local_process') as fake_run_local_process:
            fake_run_local_process.return_value = 0, []
            run_ops(state)

        fake_run_local_process.assert_called_with(
            (
                'rsync -ax --delete --rsh '
                "'ssh -o BatchMode=yes -o StrictHostKeyChecking=no '"
                " --rsync-path 'sudo -u root rsync' src vagrant@somehost:dest"
            ),
            print_output=False,
            print_prefix=inventory.get_host('somehost').print_prefix,
        )

    def test_rsync_op_failure(self):
        inventory = make_inventory(hosts=('somehost',))
        state = State(inventory, Config())
        connect_all(state)

        with patch('pyinfra.api.connectors.ssh.find_executable', lambda x: None):
            with self.assertRaises(OperationError) as context:
                add_op(state, files.rsync, 'src', 'dest')

        assert context.exception.args[0] == 'The `rsync` binary is not available on this system.'

    def test_op_cannot_change_execution_kwargs(self):
        inventory = make_inventory()

        state = State(inventory, Config())

        class NoSetDefaultDict(defaultdict):
            def setdefault(self, key, _):
                return self[key]

        state.op_meta = NoSetDefaultDict(lambda: {'serial': True})

        connect_all(state)

        with self.assertRaises(OperationValueError) as context:
            add_op(state, files.file, '/var/log/pyinfra.log', serial=False)

        assert context.exception.args[0] == 'Cannot have different values for `serial`.'


class TestOperationFailures(PatchSSHTestCase):
    def test_full_op_fail(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        add_op(state, server.shell, 'echo "hi"')

        with patch('pyinfra.api.connectors.ssh.run_shell_command') as fake_run_command:
            fake_channel = FakeChannel(1)
            fake_run_command.return_value = (
                False,
                FakeBuffer('', fake_channel),
            )

            with self.assertRaises(PyinfraError) as e:
                run_ops(state)

            assert e.exception.args[0] == 'No hosts remaining!'

            somehost = inventory.get_host('somehost')

            # Ensure the op was not flagged as success
            assert state.results[somehost]['success_ops'] == 0
            # And was flagged asn an error
            assert state.results[somehost]['error_ops'] == 1

    def test_ignore_errors_op_fail(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        add_op(state, server.shell, 'echo "hi"', ignore_errors=True)

        with patch('pyinfra.api.connectors.ssh.run_shell_command') as fake_run_command:
            fake_channel = FakeChannel(1)
            fake_run_command.return_value = (
                False,
                FakeBuffer('', fake_channel),
            )

            # This should run OK
            run_ops(state)

        somehost = inventory.get_host('somehost')

        # Ensure the op was added to results
        assert state.results[somehost]['ops'] == 1
        assert state.results[somehost]['error_ops'] == 1
        # But not as a success
        assert state.results[somehost]['success_ops'] == 0

    def test_no_invalid_op_call(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)
        pseudo_state.set(state)

        state.in_op = True
        with self.assertRaises(PyinfraError):
            server.user('someuser')

        state.in_op = False
        state.in_deploy = True
        with self.assertRaises(PyinfraError):
            server.user('someuser')


class TestOperationOrdering(PatchSSHTestCase):
    # In CLI mode, pyinfra uses *line numbers* to order operations as defined by
    # the user. This makes reasoning about user-written deploys simple and easy
    # to understand.
    def test_cli_op_line_numbers(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        state.current_deploy_filename = __file__

        pyinfra.is_cli = True
        pseudo_state.set(state)

        # Add op to both hosts
        for name in ('anotherhost', 'somehost'):
            pseudo_host.set(inventory.get_host(name))
            server.shell('echo hi')  # note this is called twice but on *the same line*

        # Add op to just the second host - using the pseudo modules such that
        # it replicates a deploy file.
        pseudo_host.set(inventory.get_host('anotherhost'))
        first_pseudo_hash = server.user('anotherhost_user').hash
        first_pseudo_call_line = getframeinfo(currentframe()).lineno - 1

        # Add op to just the first host - using the pseudo modules such that
        # it replicates a deploy file.
        pseudo_host.set(inventory.get_host('somehost'))
        second_pseudo_hash = server.user('somehost_user').hash
        second_pseudo_call_line = getframeinfo(currentframe()).lineno - 1

        pseudo_state.reset()
        pseudo_host.reset()

        pyinfra.is_cli = False

        # Ensure there are two ops
        op_order = state.get_op_order()
        assert len(op_order) == 3

        # And that the two ops above were called in the expected order
        assert op_order[1] == first_pseudo_hash
        assert op_order[2] == second_pseudo_hash

        # And that they have the expected line numbers
        assert state.op_line_numbers_to_hash.get((first_pseudo_call_line,)) == first_pseudo_hash
        assert state.op_line_numbers_to_hash.get((second_pseudo_call_line,)) == second_pseudo_hash

        # Ensure somehost has two ops and anotherhost only has the one
        assert len(state.ops[inventory.get_host('somehost')]) == 2
        assert len(state.ops[inventory.get_host('anotherhost')]) == 2

    # In API mode, pyinfra *overrides* the line numbers such that whenever an
    # operation or deploy is added it is simply appended. This makes sense as
    # the user writing the API calls has full control over execution order.
    def test_api_op_line_numbers(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        another_host = inventory.get_host('anotherhost')

        def add_another_op():
            return add_op(state, server.shell, 'echo second-op')[another_host].hash

        first_op_hash = add_op(state, server.shell, 'echo first-op')[another_host].hash
        second_op_hash = add_another_op()  # note `add_op` will be called on an earlier line

        op_order = state.get_op_order()
        assert len(op_order) == 2

        assert op_order[0] == first_op_hash
        assert op_order[1] == second_op_hash


this_filename = path.join('tests', 'test_api', 'test_api_operations.py')


class TestOperationExceptions(TestCase):
    def test_add_op_rejects_cli(self):
        pyinfra.is_cli = True

        with self.assertRaises(PyinfraError) as context:
            add_op(None, server.shell)
        call_line = getframeinfo(currentframe()).lineno - 1

        pyinfra.is_cli = False

        assert context.exception.args[0] == (
            '`add_op` should not be called when pyinfra is executing in CLI mode! '
            '(line {0} in {1})'.format(call_line, this_filename)
        )

    def test_op_call_rejects_no_cli(self):
        with self.assertRaises(PyinfraError) as context:
            server.shell()
        call_line = getframeinfo(currentframe()).lineno - 1

        assert context.exception.args[0] == (
            'API operation called without state/host: '
            'server.shell (line {0} in {1})'.format(call_line, this_filename)
        )

    def test_op_call_rejects_in_op(self):
        state = FakeState()

        pyinfra.is_cli = True
        pseudo_state.set(state)

        with self.assertRaises(PyinfraError) as context:
            server.shell()
        call_line = getframeinfo(currentframe()).lineno - 1

        pyinfra.is_cli = False
        pseudo_state.reset()

        assert context.exception.args[0] == (
            'Nested operation called without state/host: '
            'server.shell (line {0} in {1})'.format(call_line, this_filename)
        )

    def test_op_call_rejects_in_deploy(self):
        state = FakeState()
        state.in_op = False

        pyinfra.is_cli = True
        pseudo_state.set(state)

        with self.assertRaises(PyinfraError) as context:
            server.shell()
        call_line = getframeinfo(currentframe()).lineno - 1

        pyinfra.is_cli = False
        pseudo_state.reset()

        assert context.exception.args[0] == (
            'Nested deploy operation called without state/host: '
            'server.shell (line {0} in {1})'.format(call_line, this_filename)
        )
