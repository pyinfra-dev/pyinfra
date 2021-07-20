from unittest import TestCase

from pyinfra.api import Config, Inventory, State
from pyinfra.api.operation_kwargs import pop_global_op_kwargs


class TestOperationKwargs(TestCase):
    def test_get_from_config(self):
        config = Config(SUDO='config-value')
        inventory = Inventory((('somehost',), {}))

        state = State(config=config, inventory=inventory)

        kwargs, keys = pop_global_op_kwargs(state, inventory.get_host('somehost'), {})
        assert kwargs['sudo'] == 'config-value'

    def test_get_from_host(self):
        config = Config(SUDO='config-value')
        inventory = Inventory(([('somehost', {'sudo': 'host-value'})], {}))

        state = State(config=config, inventory=inventory)

        kwargs, keys = pop_global_op_kwargs(state, inventory.get_host('somehost'), {})
        assert kwargs['sudo'] == 'host-value'

    def test_get_from_state_deploy_kwargs(self):
        config = Config(SUDO='config-value')
        inventory = Inventory(([('somehost', {'sudo': 'host-value'})], {}))

        state = State(config=config, inventory=inventory)
        state.deploy_kwargs = {'sudo': 'deploy-kwarg-value'}

        kwargs, keys = pop_global_op_kwargs(state, inventory.get_host('somehost'), {})
        assert kwargs['sudo'] == 'deploy-kwarg-value'

    def test_get_from_kwargs(self):
        config = Config(SUDO='config-value')
        inventory = Inventory(([('somehost', {'sudo': 'host-value'})], {}))

        state = State(config=config, inventory=inventory)
        state.deploy_kwargs = {'sudo': 'deploy-kwarg-value'}

        kwargs, keys = pop_global_op_kwargs(
            state,
            inventory.get_host('somehost'),
            {'sudo': 'kwarg-value'},
        )
        assert kwargs['sudo'] == 'kwarg-value'
        assert 'sudo' in keys
