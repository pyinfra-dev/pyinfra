class PyinfraError(Exception):
    """
    Generic pyinfra exception.
    """


class ConnectError(PyinfraError):
    """
    Exception raised when connecting fails.
    """


class FactError(PyinfraError):
    """
    Exception raised during fact gathering staging if a fact is unable to
    generate output/change state.
    """


class FactTypeError(FactError, TypeError):
    """
    Exception raised when a fact is passed invalid argument types.
    """


class FactValueError(FactError, ValueError):
    """
    Exception raised when a fact is passed invalid argument values.
    """


class OperationError(PyinfraError):
    """
    Exception raised during fact gathering staging if an operation is unable to
    generate output/change state.
    """


class OperationTypeError(OperationError, TypeError):
    """
    Exception raised when an operation is passed invalid argument types.
    """


class OperationValueError(OperationError, ValueError):
    """
    Exception raised when an operation is passed invalid argument values.
    """


class DeployError(PyinfraError):
    """
    User exception for raising in deploys or sub deploys.
    """


class InventoryError(PyinfraError):
    """
    Exception raised for inventory related errors.
    """


class NoConnectorError(PyinfraError, ValueError):
    """
    Raised when a requested connector is missing.
    """


class NoHostError(PyinfraError, KeyError):
    """
    Raised when an inventory is missing a host.
    """


class NoGroupError(PyinfraError, KeyError):
    """
    Raised when an inventory is missing a group.
    """


class ConnectorDataTypeError(PyinfraError, TypeError):
    """
    Raised when host connector data has invalid types.
    """


class ArgumentTypeError(PyinfraError, TypeError):
    """
    Raised when global arguments are passed with invalid types.
    """
