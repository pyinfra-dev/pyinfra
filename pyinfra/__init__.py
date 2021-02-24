'''
Welcome to pyinfra.
'''

import logging


# Global flag set True by `pyinfra_cli.__main__`
is_cli = False

# Global pyinfra logger
logger = logging.getLogger('pyinfra')

# Setup package level version
from .version import __version__  # noqa

# Trigger pseudo_* creation
from . import pseudo_modules  # noqa

# Initialise base classes - this sets the pseudo modules to point at the underlying
# class objects (Host, etc), which makes ipython/etc work as expected.
pseudo_modules.init_base_classes()

# TODO: remove these! They trigger an import and index of every operation/fact. This
# is not ideal and explicit imports are much better.
from . import facts  # noqa
from . import operations  # noqa
