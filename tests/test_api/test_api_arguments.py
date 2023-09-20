from unittest import TestCase

from pyinfra.api import Config, Inventory, State
from pyinfra.api.arguments import pop_global_arguments


class TestOperationKwargs(TestCase):
    def test_get_from_config(self):
        config = Config(SUDO="config-value")
        inventory = Inventory((("somehost",), {}))

        state = State(config=config, inventory=inventory)

        kwargs, keys = pop_global_arguments({}, state=state, host=inventory.get_host("somehost"))
        assert kwargs["_sudo"] == "config-value"

    def test_get_from_host(self):
        config = Config(SUDO="config-value")
        inventory = Inventory(([("somehost", {"_sudo": "host-value"})], {}))

        state = State(config=config, inventory=inventory)

        kwargs, keys = pop_global_arguments({}, state=state, host=inventory.get_host("somehost"))
        assert kwargs["_sudo"] == "host-value"

    def test_get_from_state_deploy_kwargs(self):
        config = Config(SUDO="config-value")
        inventory = Inventory(([("somehost", {"_sudo": "host-value"})], {}))
        somehost = inventory.get_host("somehost")

        state = State(config=config, inventory=inventory)
        somehost.current_deploy_kwargs = {"_sudo": "deploy-kwarg-value"}

        kwargs, keys = pop_global_arguments({}, state=state, host=somehost)
        assert kwargs["_sudo"] == "deploy-kwarg-value"

    def test_get_from_kwargs(self):
        config = Config(SUDO="config-value")
        inventory = Inventory(([("somehost", {"_sudo": "host-value"})], {}))
        somehost = inventory.get_host("somehost")

        state = State(config=config, inventory=inventory)
        somehost.current_deploy_kwargs = {
            "_sudo": "deploy-kwarg-value",
            "_sudo_user": "deploy-kwarg-user",
        }

        kwargs, keys = pop_global_arguments(
            {"_sudo": "kwarg-value"},
            state=state,
            host=somehost,
        )
        assert kwargs["_sudo"] == "kwarg-value"
        assert kwargs["_sudo_user"] == "deploy-kwarg-user"
        assert "_sudo" in keys
