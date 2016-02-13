# pyinfra
# File: pyinfra/api/exceptions.py
# Desc: pyinfra's exceptions!


class PyinfraError(Exception):
    '''Generic pyinfra exception.'''
    pass


class OperationError(PyinfraError):
    '''
    Exception raised during fact gathering staging if an operation is unable to generate
    output/change state.
    '''
    pass
