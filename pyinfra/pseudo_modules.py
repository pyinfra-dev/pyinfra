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

import pyinfra


class PseudoModule(object):
    _module = None
    _base_module = None

    def __repr__(self):
        return 'PseudoModule({0}):{1}'.format(
            self._base_module.__name__,
            repr(self._module),
        )

    def __str__(self):
        return str(self._module)

    def __dir__(self):
        return dir(self._base_module)

    def __getattr__(self, key):
        if self._module is None:
            return getattr(self._base_module, key)
        return getattr(self._module, key)

    def __setattr__(self, key, value):
        if key in ('_module', '_base_module'):
            return super(PseudoModule, self).__setattr__(key, value)

        if self._module is None:
            raise TypeError('Cannot assign to pseudo base module')

        return setattr(self._module, key, value)

    def __iter__(self):
        return iter(self._module)

    def __len__(self):
        return len(self._module)

    def __eq__(self, other):
        return self._module == other

    def set(self, module):
        self._module = module

    def set_base(self, module):
        self._base_module = module

    def reset(self):
        self._module = None

    def isset(self):
        return self._module is not None


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
    PseudoModule()


def init_base_classes():
    from pyinfra.api import Config, Host, Inventory, State

    pseudo_config.set_base(Config)
    pseudo_host.set_base(Host)
    pseudo_inventory.set_base(Inventory)
    pseudo_state.set_base(State)
