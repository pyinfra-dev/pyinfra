from pyinfra.api import Config, State, StringCommand
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.deploy import add_deploy, deploy
from pyinfra.api.operations import run_ops
from pyinfra.operations import server

from ..paramiko_util import PatchSSHTestCase
from ..util import make_inventory


class TestDeploysApi(PatchSSHTestCase):
    def test_deploy(self):
        inventory = make_inventory()
        somehost = inventory.get_host("somehost")
        anotherhost = inventory.get_host("anotherhost")

        state = State(inventory, Config())

        # Enable printing on this test to catch any exceptions in the formatting
        state.print_output = True
        state.print_input = True
        state.print_fact_info = True
        state.print_noop_info = True

        connect_all(state)

        @deploy
        def test_deploy(state=None, host=None):
            server.shell(commands=["echo first command"])
            server.shell(commands=["echo second command"])

        add_deploy(state, test_deploy)

        op_order = state.get_op_order()

        # Ensure we have an op
        assert len(op_order) == 2

        first_op_hash = op_order[0]
        assert state.op_meta[first_op_hash]["names"] == {"test_deploy | Server/Shell"}
        assert state.ops[somehost][first_op_hash]["commands"] == [
            StringCommand("echo first command"),
        ]
        assert state.ops[anotherhost][first_op_hash]["commands"] == [
            StringCommand("echo first command"),
        ]

        second_op_hash = op_order[1]
        assert state.op_meta[second_op_hash]["names"] == {"test_deploy | Server/Shell"}
        assert state.ops[somehost][second_op_hash]["commands"] == [
            StringCommand("echo second command"),
        ]
        assert state.ops[anotherhost][second_op_hash]["commands"] == [
            StringCommand("echo second command"),
        ]

        # Ensure run ops works
        run_ops(state)

        # Ensure ops completed OK
        assert state.results[somehost]["success_ops"] == 2
        assert state.results[somehost]["ops"] == 2
        assert state.results[anotherhost]["success_ops"] == 2
        assert state.results[anotherhost]["ops"] == 2

        # And w/o errors
        assert state.results[somehost]["error_ops"] == 0
        assert state.results[anotherhost]["error_ops"] == 0

        # And with the different modes
        run_ops(state, serial=True)
        run_ops(state, no_wait=True)

        disconnect_all(state)

    def test_nested_deploy(self):
        inventory = make_inventory()
        somehost = inventory.get_host("somehost")

        state = State(inventory, Config())

        # Enable printing on this test to catch any exceptions in the formatting
        state.print_output = True
        state.print_input = True
        state.print_fact_info = True
        state.print_noop_info = True

        connect_all(state)

        @deploy
        def test_nested_deploy():
            server.shell(commands=["echo nested command"])

        @deploy
        def test_deploy():
            server.shell(commands=["echo first command"])
            test_nested_deploy()
            server.shell(commands=["echo second command"])

        add_deploy(state, test_deploy)

        op_order = state.get_op_order()

        # Ensure we have an op
        assert len(op_order) == 3

        first_op_hash = op_order[0]
        assert state.op_meta[first_op_hash]["names"] == {"test_deploy | Server/Shell"}
        assert state.ops[somehost][first_op_hash]["commands"] == [
            StringCommand("echo first command"),
        ]

        second_op_hash = op_order[1]
        assert state.op_meta[second_op_hash]["names"] == {
            "test_deploy | test_nested_deploy | Server/Shell",
        }
        assert state.ops[somehost][second_op_hash]["commands"] == [
            StringCommand("echo nested command"),
        ]

        third_op_hash = op_order[2]
        assert state.op_meta[third_op_hash]["names"] == {"test_deploy | Server/Shell"}
        assert state.ops[somehost][third_op_hash]["commands"] == [
            StringCommand("echo second command"),
        ]
