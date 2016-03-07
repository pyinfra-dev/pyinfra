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

    def __iter__(self):
        return iter(self._module)

    def set(self, module):
        self._module = module


sys.modules['pyinfra.pseudo_state'] = sys.modules['pyinfra.state'] = \
    pyinfra.pseudo_state = pyinfra.state = \
    PseudoModule()

sys.modules['pyinfra.pseudo_host'] = sys.modules['pyinfra.host'] = \
    pyinfra.pseudo_host = pyinfra.host = \
    PseudoModule()

sys.modules['pyinfra.pseudo_inventory'] = sys.modules['pyinfra.inventory'] = \
    pyinfra.pseudo_inventory = pyinfra.inventory = \
    PseudoModule()
