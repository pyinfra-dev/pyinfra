from typing import cast
from unittest import TestCase

from pyinfra.api import Config, Host, Inventory, State
from pyinfra.api.arguments import AllArguments, pop_global_arguments


class TestOperationKwargs(TestCase):
    def test_get_from_config(self):
        config = Config(SUDO="config-value")
        inventory = Inventory((("somehost",), {}))

        state = State(config=config, inventory=inventory)
        host = inventory.get_host("somehost")

        kwargs, _ = pop_global_arguments(state, host, {})
        assert kwargs.get("_sudo") == "config-value"

    def test_get_from_host(self):
        config = Config(SUDO="config-value")
        inventory = Inventory(([("somehost", {"_sudo": True})], {}))

        state = State(config=config, inventory=inventory)
        host = inventory.get_host("somehost")

        kwargs, _ = pop_global_arguments(state, host, {})
        assert kwargs.get("_sudo") is True

    def test_get_from_state_deploy_kwargs(self):
        config = Config(SUDO="config-value")
        inventory = Inventory(([("somehost", {"_sudo": False})], {}))
        somehost = inventory.get_host("somehost")
        assert isinstance(somehost, Host)

        state = State(config=config, inventory=inventory)
        host = inventory.get_host("somehost")
        somehost.current_deploy_kwargs = cast(AllArguments, {"_sudo": True})

        kwargs, keys = pop_global_arguments(state, host, {})
        assert kwargs.get("_sudo") is True

    def test_get_from_kwargs(self):
        config = Config(SUDO="config-value")
        inventory = Inventory(([("somehost", {"_sudo": False})], {}))
        somehost = inventory.get_host("somehost")
        assert isinstance(somehost, Host)

        state = State(config=config, inventory=inventory)
        somehost.current_deploy_kwargs = cast(
            AllArguments,
            {
                "_sudo": False,
                "_sudo_user": "deploy-kwarg-user",
            },
        )

        kwargs, keys = pop_global_arguments(state, somehost, {"_sudo": True})
        assert kwargs.get("_sudo") is True
        assert kwargs.get("_sudo_user") == "deploy-kwarg-user"
        assert "_sudo" in keys
