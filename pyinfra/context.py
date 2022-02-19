'''
The `ContextObject` and `ContextManager` provide context specific variables that
are imported and used throughout pyinfra and end user deploy code (CLI mode).

These variables always represent the current executing pyinfra context.
'''

from contextlib import contextmanager

from gevent.local import local


class container():
    pass


class ContextObject(object):
    _container_cls = container
    _base_cls = None

    def __init__(self):
        self._container = self._container_cls()
        self._container.module = None

    def _get_module(self):
        return self._container.module

    def __repr__(self):
        return 'ContextObject({0}):{1}'.format(
            self._base_cls.__name__,
            repr(self._get_module()),
        )

    def __str__(self):
        return str(self._get_module())

    def __dir__(self):
        return dir(self._base_cls)

    def __getattr__(self, key):
        if self._get_module() is None:
            return getattr(self._base_cls, key)
        return getattr(self._get_module(), key)

    def __setattr__(self, key, value):
        if key in ('_container', '_base_cls'):
            return super(ContextObject, self).__setattr__(key, value)

        if self._get_module() is None:
            raise TypeError('Cannot assign to pseudo base module')

        return setattr(self._get_module(), key, value)

    def __iter__(self):
        return iter(self._get_module())

    def __len__(self):
        return len(self._get_module())

    def __eq__(self, other):
        return self._get_module() == other

    def __hash__(self):
        return hash(self._get_module())


class LocalContextObject(ContextObject):
    _container_cls = local


class ContextManager(object):
    def __init__(self, key, context_cls):
        self.context = context_cls()

    def get(self):
        return self.context._container.module

    def set(self, module):
        self.context._container.module = module

    def set_base(self, module):
        self.context._base_cls = module

    def reset(self):
        self.context._container.module = None

    def isset(self):
        return self.context._container.module is not None

    @contextmanager
    def _use(self, module):
        old_module = self.get()
        self.set(module)
        yield
        self.set(old_module)


ctx_state = ContextManager('state', ContextObject)
state = ctx_state.context

ctx_config = ContextManager('config', ContextObject)
config = ctx_config.context

ctx_inventory = ContextManager('inventory', ContextObject)
inventory = ctx_inventory.context

ctx_host = ContextManager('host', LocalContextObject)
host = ctx_host.context


def init_base_classes():
    from pyinfra.api import Config, Host, Inventory, State
    ctx_config.set_base(Config)
    ctx_host.set_base(Host)
    ctx_inventory.set_base(Inventory)
    ctx_state.set_base(State)
