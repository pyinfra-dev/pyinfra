# pyinfra
# File: pyinfra/api/__init__.py
# Desc: import some stuff

from .operation import operation, operation_env # noqa
from .exception import OperationError # noqa

# Imported here but only to trigger pyinfra.host creation
# pyinfra.host is an instance of the class in host.py
from . import host # noqa
