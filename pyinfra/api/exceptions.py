# pyinfra
# File: pyinfra/api/exceptions.py
# Desc: pyinfra's exceptions!

class PyinfraException(Exception):
    pass

class OperationException(PyinfraException):
    pass

class HookException(PyinfraException):
    pass
