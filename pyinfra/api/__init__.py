# flake8: noqa
# pyinfra
# File: pyinfra/api/__init__.py
# Desc: import some stuff

'''
The pyinfra API allows you to dynamically build inventories and operations.
'''

# Triggers pyinfra.[host|state] module-class creation
from . import state
from . import host

# Operations API
from .operation import operation
from .exceptions import OperationError

# Facts API
from .facts import FactBase

# Deploy API
from .inventory import Inventory
from .config import Config
from .state import State
