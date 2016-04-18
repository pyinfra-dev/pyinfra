# flake8: noqa
# pyinfra
# File: pyinfra/__init__.py
# Desc: some global state for pyinfra

'''
Welcome to pyinfra.
'''

import logging


# pyinfra version
__version__ = '0.1.dev19'

# Global pyinfra logger
logger = logging.getLogger('pyinfra')


# Trigger pseudo_* creation
from . import pseudo_modules

# Trigger facts index
from . import facts
