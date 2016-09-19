# pyinfra
# File: pyinfra/api/exceptions.py
# Desc: pyinfra's exceptions!


class PyinfraError(Exception):
    '''
    Generic pyinfra exception.
    '''


class OperationError(PyinfraError):
    '''
    Exception raised during fact gathering staging if an operation is unable to generate
    output/change state.
    '''


class DeployError(PyinfraError):
    '''
    User exception for raising in deploys or sub deploys.
    '''


class NoHostError(PyinfraError, TypeError):
    '''
    Raised when an inventory is missing a host.
    '''


class NoGroupError(PyinfraError, TypeError):
    '''
    Raise when an inventory is missing a group.
    '''
