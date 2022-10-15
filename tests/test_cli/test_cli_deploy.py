from os import path
from random import shuffle

from pyinfra import inventory, state
from pyinfra.context import ctx_state

from ..paramiko_util import PatchSSHTestCase
from .util import run_cli


class TestCliDeploy(PatchSSHTestCase):
    def test_interdependent_deploy(self):
        ctx_state.reset()

        result = run_cli(
            "somehost",
            path.join("tests", "deploy", "deploy_interdependent.py"),
            f'--chdir={path.join("tests", "deploy")}',
        )
        assert result.exit_code == 0, result.stdout

        # Check every operation had commands/changes - this ensures that each
        # combo (add/remove/add) always had changes.
        for host, ops in state.ops.items():
            for _, op in ops.items():
                assert len(op["commands"]) > 0


class TestCliDeployState(PatchSSHTestCase):
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

            assert list(op_meta["names"])[0] == correct_op_name

            for host in state.inventory:
                if correct_host_names is True or host.name in correct_host_names:
                    self.assertIn(op_hash, host.op_hash_order)
                else:
                    self.assertNotIn(op_hash, host.op_hash_order)

    def test_deploy(self):
        task_file_path = path.join("tasks", "a_task.py")
        nested_task_path = path.join("tasks", "another_task.py")
        correct_op_name_and_host_names = [
            ("First main operation", True),  # true for all hosts
            ("Second main operation", ("somehost",)),
            ("{0} | First task operation".format(task_file_path), ("anotherhost",)),
            ("{0} | Task order loop 1".format(task_file_path), ("anotherhost",)),
            ("{0} | 2nd Task order loop 1".format(task_file_path), ("anotherhost",)),
            ("{0} | Task order loop 2".format(task_file_path), ("anotherhost",)),
            ("{0} | 2nd Task order loop 2".format(task_file_path), ("anotherhost",)),
            (
                "{0} | {1} | Second task operation".format(task_file_path, nested_task_path),
                ("anotherhost",),
            ),
            ("{0} | First task operation".format(task_file_path), True),
            ("{0} | Task order loop 1".format(task_file_path), True),
            ("{0} | 2nd Task order loop 1".format(task_file_path), True),
            ("{0} | Task order loop 2".format(task_file_path), True),
            ("{0} | 2nd Task order loop 2".format(task_file_path), True),
            ("{0} | {1} | Second task operation".format(task_file_path, nested_task_path), True),
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
        ]

        # Run 3 iterations of the test - each time shuffling the order of the
        # hosts - ensuring that the ordering has no effect on the operation order.
        for _ in range(3):
            ctx_state.reset()

            hosts = ["somehost", "anotherhost", "someotherhost"]
            shuffle(hosts)

            result = run_cli(
                ",".join(hosts),
                path.join("tests", "deploy", "deploy.py"),
                f'--chdir={path.join("tests", "deploy")}',
            )
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

            result = run_cli(
                ",".join(hosts),
                path.join("tests", "deploy", "deploy_random.py"),
                f'--chdir={path.join("tests", "deploy")}',
            )
            assert result.exit_code == 0, result.stdout

            self._assert_op_data(correct_op_name_and_host_names)

            for hostname, expected_fact_count in (
                ("somehost", 2),
                ("anotherhost", 0),
                ("someotherhost", 1),
            ):
                host = inventory.get_host(hostname)
                assert len(host.facts) == expected_fact_count
