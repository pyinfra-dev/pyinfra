# pyinfra
# File: pyinfra/api/exceptions.py
# Desc: pyinfra's exceptions!


class PyinfraException(Exception):
    '''Generic pyinfra exception.'''
    pass


class OperationException(PyinfraException):
    '''
    Exception raised during fact gathering staging if an operation is unable to generate
    output/change state.
    '''
    pass


class HookException(PyinfraException):
    '''Exception raised when encounting errors in deploy hooks.'''
    pass
