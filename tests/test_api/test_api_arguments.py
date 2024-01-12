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
        inventory = Inventory(([("somehost", {"_sudo": True})], {}))

        state = State(config=config, inventory=inventory)

        kwargs, keys = pop_global_arguments({}, state=state, host=inventory.get_host("somehost"))
        assert kwargs["_sudo"] is True

    def test_get_from_state_deploy_kwargs(self):
        config = Config(SUDO="config-value")
        inventory = Inventory(([("somehost", {"_sudo": False})], {}))
        somehost = inventory.get_host("somehost")

        state = State(config=config, inventory=inventory)
        somehost.current_deploy_kwargs = {"_sudo": True}

        kwargs, keys = pop_global_arguments({}, state=state, host=somehost)
        assert kwargs["_sudo"] is True

    def test_get_from_kwargs(self):
        config = Config(SUDO="config-value")
        inventory = Inventory(([("somehost", {"_sudo": False})], {}))
        somehost = inventory.get_host("somehost")

        state = State(config=config, inventory=inventory)
        somehost.current_deploy_kwargs = {
            "_sudo": False,
            "_sudo_user": "deploy-kwarg-user",
        }

        kwargs, keys = pop_global_arguments(
            {"_sudo": True},
            state=state,
            host=somehost,
        )
        assert kwargs["_sudo"] is True
        assert kwargs["_sudo_user"] == "deploy-kwarg-user"
        assert "_sudo" in keys
