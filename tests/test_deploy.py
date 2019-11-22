from os import path
from random import shuffle

import pyinfra

from pyinfra import pseudo_state
from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra_cli.util import load_deploy_file

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
            ('Order loop 1', True),
            ('2nd Order loop 1', True),
            ('Order loop 2', True),
            ('2nd Order loop 2', True),
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

        self.assertEqual(
            len(correct_op_name_and_host_names), len(op_order),
            'Incorrect number of operations detected',
        )

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
