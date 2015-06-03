# pyinfra
# File: pyinfra/api/__init__.py
# Desc: import some stuff

from .operation import operation, operation_env # noqa
from .exceptions import OperationError # noqa

# Imported here but only to trigger pyinfra.[config|host] creation
# pyinfra.[config|host] is an instance of the class in [config|host].py
from . import config # noqa
from . import host # noqa
