from unittest import TestCase

from paramiko import SSHException

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import NoGroupError, NoHostError, PyinfraError

from ..paramiko_util import PatchSSHTestCase
from ..util import make_inventory


class TestInventoryApi(TestCase):
    def test_inventory_creation(self):
        inventory = make_inventory()

        # Check length
        assert len(inventory.hosts) == 2

        # Get a host
        host = inventory.get_host('somehost')
        assert host.data.ssh_user == 'vagrant'

        # Check our group data
        assert inventory.get_group_data('test_group') == {
            'group_data': 'hello world',
        }

    def test_tuple_host_group_inventory_creation(self):
        inventory = make_inventory(
            hosts=[
                ('somehost', {'some_data': 'hello'}),
            ],
            tuple_group=([
                ('somehost', {'another_data': 'world'}),
            ], {
                'tuple_group_data': 'word',
            }),
        )

        # Check host data
        host = inventory.get_host('somehost')
        assert host.data.some_data == 'hello'
        assert host.data.another_data == 'world'

        # Check group data
        assert host.data.tuple_group_data == 'word'

    def test_host_and_group_errors(self):
        inventory = make_inventory()

        with self.assertRaises(NoHostError):
            inventory.get_host('i-dont-exist')

        with self.assertRaises(NoGroupError):
            inventory.get_group('i-dont-exist')


class TestStateApi(PatchSSHTestCase):
    def test_fail_percent(self):
        inventory = make_inventory((
            'somehost',
            ('thinghost', {'ssh_hostname': SSHException}),
            'anotherhost',
        ))
        state = State(inventory, Config(FAIL_PERCENT=1))

        # Ensure we would fail at this point
        with self.assertRaises(PyinfraError) as context:
            connect_all(state)

        assert context.exception.args[0] == 'Over 1% of hosts failed (33%)'

        # Ensure the other two did connect
        assert len(state.active_hosts) == 2
