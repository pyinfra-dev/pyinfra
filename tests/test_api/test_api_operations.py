from inspect import currentframe, getframeinfo

from mock import mock_open, patch

from pyinfra import pseudo_host, pseudo_state
from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.modules import files, python, server

from ..paramiko_util import (
    FakeBuffer,
    FakeChannel,
    PatchSSHTestCase,
)
from ..util import make_inventory


class TestOperationsApi(PatchSSHTestCase):
    def test_op(self):
        inventory = make_inventory()
        somehost = inventory.get_host('somehost')
        anotherhost = inventory.get_host('anotherhost')

        state = State(inventory, Config())

        # Enable printing on this test to catch any exceptions in the formatting
        state.print_output = True
        state.print_fact_info = True
        state.print_fact_output = True

        connect_all(state)

        add_op(
            state, files.file,
            '/var/log/pyinfra.log',
            user='pyinfra',
            group='pyinfra',
            mode='644',
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
        self.assertEqual(len(op_order), 1)

        first_op_hash = op_order[0]

        # Ensure the op name
        self.assertEqual(
            state.op_meta[first_op_hash]['names'],
            {'Files/File'},
        )

        # Ensure the commands
        self.assertEqual(
            state.ops[somehost][first_op_hash]['commands'],
            [
                'touch /var/log/pyinfra.log',
                'chmod 644 /var/log/pyinfra.log',
                'chown pyinfra:pyinfra /var/log/pyinfra.log',
            ],
        )

        # Ensure the meta
        meta = state.op_meta[first_op_hash]
        self.assertEqual(meta['sudo'], True)
        self.assertEqual(meta['sudo_user'], 'test_sudo')
        self.assertEqual(meta['su_user'], 'test_su')
        self.assertEqual(meta['ignore_errors'], True)

        # Ensure run ops works
        run_ops(state)

        # Ensure ops completed OK
        self.assertEqual(state.results[somehost]['success_ops'], 1)
        self.assertEqual(state.results[somehost]['ops'], 1)
        self.assertEqual(state.results[anotherhost]['success_ops'], 1)
        self.assertEqual(state.results[anotherhost]['ops'], 1)

        # And w/o errors
        self.assertEqual(state.results[somehost]['error_ops'], 0)
        self.assertEqual(state.results[anotherhost]['error_ops'], 0)

        # And with the different modes
        run_ops(state, serial=True)
        run_ops(state, no_wait=True)

    def test_file_upload_op(self):
        inventory = make_inventory()

        state = State(inventory, Config())
        connect_all(state)

        with patch('pyinfra.modules.files.path.isfile', lambda *args, **kwargs: True):
            # Test normal
            add_op(
                state, files.put,
                {'First op name'},
                'files/file.txt',
                '/home/vagrant/file.txt',
            )

            # And with sudo
            add_op(
                state, files.put,
                'files/file.txt',
                '/home/vagrant/file.txt',
                sudo=True,
                sudo_user='pyinfra',
            )

            # And with su
            add_op(
                state, files.put,
                'files/file.txt',
                '/home/vagrant/file.txt',
                sudo=True,
                su_user='pyinfra',
            )

        op_order = state.get_op_order()

        # Ensure we have all ops
        self.assertEqual(len(op_order), 3)

        first_op_hash = op_order[0]

        # Ensure first op is the right one
        self.assertEqual(
            state.op_meta[first_op_hash]['names'],
            {'First op name'},
        )

        somehost = inventory.get_host('somehost')
        anotherhost = inventory.get_host('anotherhost')

        # Ensure first op has the right (upload) command
        self.assertEqual(
            state.ops[somehost][first_op_hash]['commands'],
            [
                ('upload', 'files/file.txt', '/home/vagrant/file.txt'),
            ],
        )

        # Ensure second op has sudo/sudo_user
        self.assertEqual(state.op_meta[op_order[1]]['sudo'], True)
        self.assertEqual(state.op_meta[op_order[1]]['sudo_user'], 'pyinfra')

        # Ensure third has su_user
        self.assertEqual(state.op_meta[op_order[2]]['su_user'], 'pyinfra')

        # Check run ops works
        with patch('pyinfra.api.util.open', mock_open(read_data='test!'), create=True):
            run_ops(state)

        # Ensure ops completed OK
        self.assertEqual(state.results[somehost]['success_ops'], 3)
        self.assertEqual(state.results[somehost]['ops'], 3)
        self.assertEqual(state.results[anotherhost]['success_ops'], 3)
        self.assertEqual(state.results[anotherhost]['ops'], 3)

        # And w/o errors
        self.assertEqual(state.results[somehost]['error_ops'], 0)
        self.assertEqual(state.results[anotherhost]['error_ops'], 0)

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
        self.assertEqual(len(state.get_op_order()), 1)

        run_ops(state)

        assert is_called

    def test_run_once_serial_op(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        # Add a run once op
        add_op(state, server.shell, 'echo "hi"', run_once=True, serial=True)

        # Ensure it's added to op_order
        self.assertEqual(len(state.get_op_order()), 1)

        somehost = inventory.get_host('somehost')
        anotherhost = inventory.get_host('anotherhost')

        # Ensure between the two hosts we only run the one op
        self.assertEqual(len(state.ops[somehost]) + len(state.ops[anotherhost]), 1)

        # Check run works
        run_ops(state)

        self.assertEqual((
            state.results[somehost]['success_ops']
            + state.results[anotherhost]['success_ops']
        ), 1)


class TestOperationLimits(PatchSSHTestCase):
    def test_op_hosts_limit(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        # Add op to both hosts
        add_op(state, server.shell, 'echo "hi"')

        # Add op to just the first host
        add_op(
            state, server.user,
            'somehost_user',
            hosts=inventory['somehost'],
        )

        # Ensure there are two ops
        self.assertEqual(len(state.get_op_order()), 2)

        # Ensure somehost has two ops and anotherhost only has the one
        self.assertEqual(len(state.ops[inventory.get_host('somehost')]), 2)
        self.assertEqual(len(state.ops[inventory.get_host('anotherhost')]), 1)

    def test_op_state_hosts_limit(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        # Add op to both hosts
        add_op(state, server.shell, 'echo "hi"')

        # Add op to just the first host
        with state.hosts('test_group'):
            add_op(
                state, server.user,
                'somehost_user',
            )

            # Now, also limited but set hosts to the non-limited hosts, which
            # should mean this operation applies to no hosts.
            add_op(
                state, server.user,
                'somehost_user',
                hosts=inventory.get_host('anotherhost'),
            )

        # Ensure there are three ops
        self.assertEqual(len(state.get_op_order()), 3)

        # Ensure somehost has two ops and anotherhost only has the one
        self.assertEqual(len(state.ops[inventory.get_host('somehost')]), 2)
        self.assertEqual(len(state.ops[inventory.get_host('anotherhost')]), 1)


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

            self.assertEqual(e.exception.args[0], 'No hosts remaining!')

            somehost = inventory.get_host('somehost')

            # Ensure the op was not flagged as success
            self.assertEqual(state.results[somehost]['success_ops'], 0)
            # And was flagged asn an error
            self.assertEqual(state.results[somehost]['error_ops'], 1)

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
            self.assertEqual(state.results[somehost]['ops'], 1)
            self.assertEqual(state.results[somehost]['error_ops'], 1)
            # But not as a success
            self.assertEqual(state.results[somehost]['success_ops'], 0)

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
    def test_op_line_numbers(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        # Add op to both hosts
        add_op(state, server.shell, 'echo "hi"')

        # Add op to just the second host - using the pseudo modules such that
        # it replicates a deploy file.
        pseudo_state.set(state)
        pseudo_host.set(inventory['anotherhost'])
        first_pseudo_hash = server.user('anotherhost_user').hash
        first_pseudo_call_line = getframeinfo(currentframe()).lineno - 1

        # Add op to just the first host - using the pseudo modules such that
        # it replicates a deploy file.
        pseudo_state.set(state)
        pseudo_host.set(inventory['somehost'])
        second_pseudo_hash = server.user('somehost_user').hash
        second_pseudo_call_line = getframeinfo(currentframe()).lineno - 1

        pseudo_state.reset()
        pseudo_host.reset()

        # Ensure there are two ops
        op_order = state.get_op_order()
        self.assertEqual(len(op_order), 3)

        # And that the two ops above were called in the expected order
        self.assertEqual(op_order[1], first_pseudo_hash)
        self.assertEqual(op_order[2], second_pseudo_hash)

        # And that they have the expected line numbers
        self.assertEqual(
            state.op_line_numbers_to_hash.get((0, first_pseudo_call_line)),
            first_pseudo_hash,
        )
        self.assertEqual(
            state.op_line_numbers_to_hash.get((0, second_pseudo_call_line)),
            second_pseudo_hash,
        )

        # Ensure somehost has two ops and anotherhost only has the one
        self.assertEqual(len(state.ops[inventory.get_host('somehost')]), 2)
        self.assertEqual(len(state.ops[inventory.get_host('anotherhost')]), 2)
