import importlib
import typing

__all__ = [
    "FileDownloadCommand",
    "FileUploadCommand",
    "FunctionCommand",
    "MaskString",
    "QuoteString",
    "RsyncCommand",
    "StringCommand",
    "Config",
    "deploy",
    "DeployError",
    "FactError",
    "FactTypeError",
    "FactValueError",
    "FactProcessError",
    "InventoryError",
    "OperationError",
    "OperationTypeError",
    "OperationValueError",
    "FactBase",
    "ShortFactBase",
    "Host",
    "Inventory",
    "operation",
    "BaseStateCallback",
    "State",
]

_module_map = {
    "FileDownloadCommand": ".command",
    "FileUploadCommand": ".command",
    "FunctionCommand": ".command",
    "MaskString": ".command",
    "QuoteString": ".command",
    "RsyncCommand": ".command",
    "StringCommand": ".command",
    "Config": ".config",
    "deploy": ".deploy",
    "DeployError": ".exceptions",
    "FactError": ".exceptions",
    "FactTypeError": ".exceptions",
    "FactValueError": ".exceptions",
    "FactProcessError": ".exceptions",
    "InventoryError": ".exceptions",
    "OperationError": ".exceptions",
    "OperationTypeError": ".exceptions",
    "OperationValueError": ".exceptions",
    "FactBase": ".facts",
    "ShortFactBase": ".facts",
    "Host": ".host",
    "Inventory": ".inventory",
    "operation": ".operation",
    "BaseStateCallback": ".state",
    "State": ".state",
}

if typing.TYPE_CHECKING:
    from .command import (  # noqa: F401
        FileDownloadCommand,  # noqa: F401 # pragma: no cover
        FileUploadCommand,
        FunctionCommand,
        MaskString,
        QuoteString,
        RsyncCommand,
        StringCommand,
    )
    from .config import Config  # noqa: F401 # pragma: no cover
    from .deploy import deploy  # noqa: F401 # pragma: no cover
    from .exceptions import (  # noqa: F401
        DeployError,  # noqa: F401 # pragma: no cover
        FactError,
        FactProcessError,
        FactTypeError,
        FactValueError,
        InventoryError,
        OperationError,
        OperationTypeError,
        OperationValueError,
    )
    from .facts import FactBase, ShortFactBase  # noqa: F401 # pragma: no cover
    from .host import Host  # noqa: F401 # pragma: no cover
    from .inventory import Inventory  # noqa: F401 # pragma: no cover
    from .operation import operation  # noqa: F401 # pragma: no cover
    from .state import BaseStateCallback, State  # noqa: F401 # pragma: no cover


def __getattr__(name):
    if name in _module_map:
        module = importlib.import_module(_module_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return __all__


# from .command import FileDownloadCommand  # noqa: F401 # pragma: no cover
# from .command import (  # noqa: F401
#     FileUploadCommand,
#     FunctionCommand,
#     MaskString,
#     QuoteString,
#     RsyncCommand,
#     StringCommand,
# )
# from .config import Config  # noqa: F401 # pragma: no cover
# from .deploy import deploy  # noqa: F401 # pragma: no cover
# from .exceptions import DeployError  # noqa: F401 # pragma: no cover
# from .exceptions import (  # noqa: F401
#     FactError,
#     FactTypeError,
#     FactValueError,
#     FactProcessError,
#     InventoryError,
#     OperationError,
#     OperationTypeError,
#     OperationValueError,
# )
# from .facts import FactBase, ShortFactBase  # noqa: F401 # pragma: no cover
# from .host import Host  # noqa: F401 # pragma: no cover
# from .inventory import Inventory  # noqa: F401 # pragma: no cover
# from .operation import operation  # noqa: F401 # pragma: no cover
# from .state import BaseStateCallback, State  # noqa: F401 # pragma: no cover
