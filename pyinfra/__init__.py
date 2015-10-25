# pyinfra
# File: pyinfra/__init__.py
# Desc: some global state for pyinfra

'''
Welcome to pyinfra.
'''

import logging


# Global pyinfra logger
logger = logging.getLogger('pyinfra')

# Make everything available
from . import facts, modules, api # noqa
