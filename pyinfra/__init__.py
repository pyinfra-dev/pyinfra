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

# Trigger fact index creation
from . import facts  # noqa

# Trigger module imports
from . import modules  # noqa # pragma: no cover
