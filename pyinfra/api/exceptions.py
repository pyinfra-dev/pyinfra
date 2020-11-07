class PyinfraError(Exception):
    '''
    Generic pyinfra exception.
    '''


class ConnectError(PyinfraError):
    '''
    Exception raised when connecting fails.
    '''


class OperationError(PyinfraError):
    '''
    Exception raised during fact gathering staging if an operation is unable to
    generate output/change state.
    '''


class OperationTypeError(OperationError, TypeError):
    '''
    Exception raised when an operation is passed invalid argument types.
    '''


class OperationValueError(OperationError, ValueError):
    '''
    Exception raised when an operation is passed invalid argument values.
    '''


class DeployError(PyinfraError):
    '''
    User exception for raising in deploys or sub deploys.
    '''


class InventoryError(PyinfraError):
    '''
    Exception raised for inventory related errors.
    '''


class NoConnectorError(PyinfraError, TypeError):
    '''
    Raised when a requested connector is missing.
    '''


class NoHostError(PyinfraError, TypeError):
    '''
    Raised when an inventory is missing a host.
    '''


class NoGroupError(PyinfraError, TypeError):
    '''
    Raise when an inventory is missing a group.
    '''
