"""
The `ContextObject` and `ContextManager` provide context specific variables that
are imported and used throughout pyinfra and end user deploy code (CLI mode).

These variables always represent the current executing pyinfra context.
"""

from contextlib import contextmanager
from types import ModuleType
from typing import TYPE_CHECKING

from gevent.local import local
from typing_extensions import override

if TYPE_CHECKING:
    from pyinfra.api.config import Config
    from pyinfra.api.host import Host
    from pyinfra.api.inventory import Inventory
    from pyinfra.api.state import State


class container:
    module = None


class ContextObject:
    _container_cls = container
    _base_cls: ModuleType

    def __init__(self) -> None:
        self._container = self._container_cls()
        self._container.module = None

    def _get_module(self):
        return self._container.module

    @override
    def __repr__(self):
        return "ContextObject({0}):{1}".format(
            self._base_cls.__name__,
            repr(self._get_module()),
        )

    @override
    def __str__(self):
        return str(self._get_module())

    @override
    def __dir__(self):
        return dir(self._base_cls)

    def __getattr__(self, key):
        if self._get_module() is None:
            return getattr(self._base_cls, key)
        return getattr(self._get_module(), key)

    @override
    def __setattr__(self, key, value):
        if key in ("_container", "_base_cls"):
            return super().__setattr__(key, value)

        mod = self._get_module()
        if mod is None:
            raise TypeError("Cannot assign to context base module")
        return setattr(mod, key, value)

    def __iter__(self):
        mod = self._get_module()
        if mod is None:
            raise ValueError("Context not set")
        return iter(mod)

    def __len__(self):
        mod = self._get_module()
        if mod is None:
            raise ValueError("Context not set")
        return len(mod)

    @override
    def __eq__(self, other):
        return self._get_module() == other

    @override
    def __hash__(self):
        return hash(self._get_module())


class LocalContextObject(ContextObject):
    _container_cls = local


class ContextManager:
    def __init__(self, key, context_cls):
        self.context = context_cls()

    def get(self):
        return getattr(self.context._container, "module", None)

    def set(self, module):
        self.context._container.module = module

    def set_base(self, module):
        self.context._base_cls = module

    def reset(self) -> None:
        self.context._container.module = None

    def isset(self):
        return self.get() is not None

    @contextmanager
    def use(self, module):
        old_module = self.get()
        if old_module is module:
            yield  # if we're double-setting, nothing to do
            return
        self.set(module)
        yield
        self.set(old_module)


ctx_state = ContextManager("state", ContextObject)
state: "State" = ctx_state.context

ctx_inventory = ContextManager("inventory", ContextObject)
inventory: "Inventory" = ctx_inventory.context

# Config can be modified mid-deploy, so we use a local object here which
# is based on a copy of the state config.
ctx_config = ContextManager("config", LocalContextObject)
config: "Config" = ctx_config.context

# Hosts are prepared in parallel each in a greenlet, so we use a local to
# point at different host objects in each greenlet.
ctx_host = ContextManager("host", LocalContextObject)
host: "Host" = ctx_host.context


def init_base_classes() -> None:
    from pyinfra.api import Config, Host, Inventory, State

    ctx_config.set_base(Config)
    ctx_inventory.set_base(Inventory)
    ctx_host.set_base(Host)
    ctx_state.set_base(State)
