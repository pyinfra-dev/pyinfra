# pyinfra
# File: pyinfra/__init__.py
# Desc: some global state for pyinfra

import logging


# Load the modules
from .modules import *

# Global logger
logger = logging.getLogger('pyinfra')

# Internal states
_current_server = None
_connections = {}
_commands = {}
_facts = {}
