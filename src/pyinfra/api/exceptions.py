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


class FactProcessError(FactError, RuntimeError):
    """
    Exception raised when the data gathered for a fact cannot be processed.
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


class NestedOperationError(OperationError):
    """
    Exception raised when a nested (immediately executed) operation fails.
    """


class FactNotCollected(FactError):
    """
    Base exception raised when a fact could not be collected (e.g. binary absent
    on the remote host, or the fact was skipped by a condition).
    """


class MissingCommandError(FactNotCollected):
    """
    Exception raised when ``requires_command`` specifies a binary that is
    not present on the remote host.  The fact returns its ``default()`` value
    instead of raising, unless explicitly configured otherwise.
    """

    def __init__(self, command: str) -> None:
        self.command = command
        super().__init__(f"Command not found on remote host: {command}")


class FactPreconditionError(FactNotCollected):
    """
    Exception raised when a fact's ``check_preconditions()`` returns a reason string
    (e.g. a kernel module is not loaded).  Like ``MissingCommandError``, this is
    silenced during the prepare phase and re-raised during execute.
    """

    def __init__(self, fact_cls: type, reason: str) -> None:
        self.fact_cls = fact_cls
        self.reason = reason
        super().__init__(f"Fact precondition not satisfied ({fact_cls.__name__}): {reason}")


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
