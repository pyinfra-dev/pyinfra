from os import path
from random import shuffle

from pyinfra import state
from pyinfra.context import ctx_state

from ..paramiko_util import PatchSSHTestCase
from .util import run_cli


class TestCliDeployState(PatchSSHTestCase):
    def _run_cli(self, hosts, filename):
        return run_cli(
            "-y",
            ",".join(hosts),
            path.join("tests", "test_cli", "deploy", filename),
            f'--chdir={path.join("tests", "test_cli", "deploy")}',
        )

    def _assert_op_data(self, correct_op_name_and_host_names):
        op_order = state.get_op_order()

        assert len(correct_op_name_and_host_names) == len(
            op_order,
        ), "Incorrect number of operations detected"

        for i, (correct_op_name, correct_host_names) in enumerate(
            correct_op_name_and_host_names,
        ):
            op_hash = op_order[i]
            op_meta = state.op_meta[op_hash]

            assert list(op_meta.names)[0] == correct_op_name

            for host in state.inventory:
                executed = False
                host_op = state.ops[host].get(op_hash)
                if host_op:
                    executed = host_op.operation_meta.executed
                if correct_host_names is True or host.name in correct_host_names:
                    assert executed is True
                else:
                    assert executed is False

    def test_deploy(self):
        a_task_file_path = path.join("tasks", "a_task.py")
        b_task_file_path = path.join("tasks", "b_task.py")
        nested_task_path = path.join("tasks", "another_task.py")
        correct_op_name_and_host_names = [
            ("First main operation", True),  # true for all hosts
            ("Second main operation", ("somehost",)),
            ("{0} | First task operation".format(a_task_file_path), ("anotherhost",)),
            ("{0} | Task order loop 1".format(a_task_file_path), ("anotherhost",)),
            ("{0} | 2nd Task order loop 1".format(a_task_file_path), ("anotherhost",)),
            ("{0} | Task order loop 2".format(a_task_file_path), ("anotherhost",)),
            ("{0} | 2nd Task order loop 2".format(a_task_file_path), ("anotherhost",)),
            (
                "{0} | {1} | Second task operation".format(a_task_file_path, nested_task_path),
                ("anotherhost",),
            ),
            ("{0} | First task operation".format(a_task_file_path), True),
            ("{0} | Task order loop 1".format(a_task_file_path), True),
            ("{0} | 2nd Task order loop 1".format(a_task_file_path), True),
            ("{0} | Task order loop 2".format(a_task_file_path), True),
            ("{0} | 2nd Task order loop 2".format(a_task_file_path), True),
            ("{0} | {1} | Second task operation".format(a_task_file_path, nested_task_path), True),
            ("{0} | Important task operation".format(b_task_file_path), True),
            ("My deploy | First deploy operation", True),
            ("My deploy | My nested deploy | First nested deploy operation", True),
            ("My deploy | Second deploy operation", True),
            ("Loop-0 main operation", True),
            ("Loop-1 main operation", True),
            ("Third main operation", True),
            ("Order loop 1", True),
            ("Nested order loop 1/1", ("anotherhost",)),
            ("Nested order loop 1/2", ("anotherhost",)),
            ("Order loop 2", True),
            ("Nested order loop 2/1", ("somehost", "anotherhost")),
            ("Nested order loop 2/2", ("somehost", "anotherhost")),
            ("Final limited operation", ("somehost",)),
            ("Second final limited operation", ("anotherhost", "someotherhost")),
        ]

        # Run 3 iterations of the test - each time shuffling the order of the
        # hosts - ensuring that the ordering has no effect on the operation order.
        for _ in range(3):
            ctx_state.reset()

            hosts = ["somehost", "anotherhost", "someotherhost"]
            shuffle(hosts)

            result = self._run_cli(hosts, "deploy.py")
            assert result.exit_code == 0, result.stdout

            self._assert_op_data(correct_op_name_and_host_names)

    def test_random_deploy(self):
        correct_op_name_and_host_names = [
            ("First main operation", True),
            ("Second main somehost operation", ("somehost",)),
            ("Second main anotherhost operation", ("anotherhost",)),
            ("Function call operation", True),
            ("Third main operation", True),
            ("First nested operation", True),
            ("Second nested anotherhost operation", ("anotherhost",)),
            ("Second nested somehost operation", ("somehost",)),
        ]

        # Run 3 iterations of the test - each time shuffling the order of the
        # hosts - ensuring that the ordering has no effect on the operation order.
        for _ in range(3):
            ctx_state.reset()

            hosts = ["somehost", "anotherhost", "someotherhost"]
            shuffle(hosts)

            result = self._run_cli(hosts, "deploy_random.py")
            assert result.exit_code == 0, result.stdout

            self._assert_op_data(correct_op_name_and_host_names)
