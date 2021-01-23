'''
Welcome to pyinfra.
'''

import logging


# Global flag set True by `pyinfra_cli.__main__`
is_cli = False

# Global pyinfra logger
logger = logging.getLogger('pyinfra')

from . import pseudo_modules  # noqa: E402
from .version import __version__  # noqa: E402, F401

# Setup pseudo modules
state = pseudo_state = pseudo_modules.pseudo_state
host = pseudo_host = pseudo_modules.pseudo_host
inventory = pseudo_inventory = pseudo_modules.pseudo_inventory

# Initialise base classes - this sets the pseudo modules to point at the underlying
# class objects (Host, etc), which makes ipython/etc work as expected.
pseudo_modules.init_base_classes()

# TODO: remove this once we have explicit fact importing (break in v2)
# Trigger fact/operations index creation
from . import facts  # noqa
from . import operations  # noqa # pragma: no cover
