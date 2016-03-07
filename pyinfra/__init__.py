# flake8: noqa
# pyinfra
# File: pyinfra/__init__.py
# Desc: some global state for pyinfra

'''
Welcome to pyinfra.
'''

import logging


# Global pyinfra logger
logger = logging.getLogger('pyinfra')


# Trigger pseudo_* creation
from . import pseudo_modules

# Trigger facts index
from . import facts
