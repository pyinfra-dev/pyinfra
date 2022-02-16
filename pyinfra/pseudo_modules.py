'''
These three pseudo modules (state, inventory, host) are used throughout pyinfra
and provide the magic that means "from pyinfra import host" inside a deploy
file always represents the *current* host being executed, ie these modules are
dynamic and change during execution of pyinfra.

Although CLI only when in use, these are bundled into the main pyinfra package
as they are utilised throughout (to determine the current state/host when
executing in CLI mode).
'''

import sys
from contextlib import contextmanager

from gevent.local import local

import pyinfra


class container():
    pass


class PseudoModule(object):
    _container_cls = container
    _base_cls = None

    def __init__(self):
        self._container = self._container_cls()
        self._container.module = None

    def _get_module(self):
        return self._container.module

    def __repr__(self):
        return 'PseudoModule({0}):{1}'.format(
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
            return super(PseudoModule, self).__setattr__(key, value)

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

    def set(self, module):
        self._container.module = module

    def set_base(self, module):
        self._base_cls = module

    def reset(self):
        self._container.module = None

    def isset(self):
        return self._container.module is not None

    @contextmanager
    def _use(self, module):
        old_module = self._container.module
        self._container.module = module

        yield

        self._container.module = old_module


class PseudoLocalModule(PseudoModule):
    _container_cls = local


# The current deploy state
pseudo_state = \
    sys.modules['pyinfra.pseudo_state'] = sys.modules['pyinfra.state'] = \
    pyinfra.pseudo_state = pyinfra.state = \
    PseudoModule()

# The current deploy config
pseudo_config = \
    sys.modules['pyinfra.pseudo_config'] = sys.modules['pyinfra.config'] = \
    pyinfra.pseudo_config = pyinfra.config = \
    PseudoModule()

# The current deploy inventory
pseudo_inventory = \
    sys.modules['pyinfra.pseudo_inventory'] = sys.modules['pyinfra.inventory'] = \
    pyinfra.pseudo_inventory = pyinfra.inventory = \
    PseudoModule()

# The current target host
pseudo_host = \
    sys.modules['pyinfra.pseudo_host'] = sys.modules['pyinfra.host'] = \
    pyinfra.pseudo_host = pyinfra.host = \
    PseudoLocalModule()


def init_base_classes():
    from pyinfra.api import Config, Host, Inventory, State

    pseudo_config.set_base(Config)
    pseudo_host.set_base(Host)
    pseudo_inventory.set_base(Inventory)
    pseudo_state.set_base(State)
