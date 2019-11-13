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

    def __getattr__(self, key):
        return getattr(self._module, key)

    def __setattr__(self, key, value):
        if key == '_module':
            return object.__setattr__(self, key, value)

        setattr(self._module, key, value)

    def __getitem__(self, key):
        return self._module[key]

    def __iter__(self):
        return iter(self._module)

    def __len__(self):
        return len(self._module)

    def __eq__(self, other):
        return self._module == other

    def set(self, module):
        self._module = module

    def reset(self):
        self._module = None

    def isset(self):
        return self._module is not None


# The current deploy state
sys.modules['pyinfra.pseudo_state'] = sys.modules['pyinfra.state'] = \
    pyinfra.pseudo_state = pyinfra.state = \
    PseudoModule()

# The current deploy inventory
sys.modules['pyinfra.pseudo_inventory'] = sys.modules['pyinfra.inventory'] = \
    pyinfra.pseudo_inventory = pyinfra.inventory = \
    PseudoModule()

# The current target host
sys.modules['pyinfra.pseudo_host'] = sys.modules['pyinfra.host'] = \
    pyinfra.pseudo_host = pyinfra.host = \
    PseudoModule()
