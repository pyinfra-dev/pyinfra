import json

from unittest import TestCase

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.host import Host
from pyinfra.api.operation import add_op
from pyinfra.modules import server
from pyinfra_cli.prints import (
    jsonify,
    print_facts,
    print_facts_list,
    print_inventory,
    print_meta,
    print_operations_list,
    print_results,
    print_state_facts,
    print_state_operations,
)

from .paramiko_util import PatchSSHTestCase
from .util import make_inventory


class TestCliPrints(TestCase):
    def test_jsonify(self):
        fake_host = Host('hostname', None, None, None)

        data = {
            fake_host: None,
        }

        assert jsonify(data) == json.dumps({'hostname': None})

    def test_print_facts_list_works(self):
        '''
        Simply checks printing the facts list works - no output check!
        '''

        print_facts_list()

    def test_print_operations_list_works(self):
        '''
        Simply checks printing the operations list works - no output check!
        '''

        print_operations_list()

    def test_print_facts_works(self):
        facts = {
            'name': 'value',
        }

        print_facts(facts)


class TestCliPrintState(PatchSSHTestCase):
    def test_print_state_works(self):
        '''
        Simply checks printing operation state works - no output check!
        '''

        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        # Add op to both hosts
        add_op(state, server.shell, 'echo "hi"')

        print_state_facts(state)
        print_state_operations(state)
        print_inventory(state)
        print_meta(state)
        print_results(state)
