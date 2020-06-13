from pyinfra import logger
from pyinfra.operations import *  # noqa: F401,F403
from pyinfra.operations import __all__

__all__ = __all__

logger.warning('Use of `pyinfra.modules` is deprecated, please use `pyinfra.operations`.')
