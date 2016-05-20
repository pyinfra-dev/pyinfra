# pyinfra
# File: pyinfra/pseudo_modules.py
# Desc: essentially a hack that provides dynamic imports for the current deploy (CLI only)

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
