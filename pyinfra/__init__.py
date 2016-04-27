# pyinfra
# File: pyinfra/__init__.py
# Desc: some global state for pyinfra

'''
Welcome to pyinfra.
'''

import logging


# Global pyinfra logger
logger = logging.getLogger('pyinfra')

# Setup package level version
from .version import __version__  # noqa

# Trigger pseudo_* creation
from . import pseudo_modules  # noqa

# Trigger fact index creation
from . import facts  # noqa
