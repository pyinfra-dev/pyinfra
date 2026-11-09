"""
Welcome to pyinfra.
"""

import logging

# Global flag set True by `pyinfra_cli.__main__`
is_cli = False

# Global pyinfra logger
logger = logging.getLogger("pyinfra")

# Trigger context module creation. The context objects are re-exported with
# redundant aliases so type checkers treat them as public (``from pyinfra import host``).
from .context import config as config  # noqa
from .context import host as host  # noqa
from .context import init_base_classes  # noqa
from .context import inventory as inventory  # noqa
from .context import state as state  # noqa

# Setup package level version
from .version import __version__ as __version__  # noqa

# Initialise base classes - this sets the context modules to point at the underlying
# class objects (Host, etc), which makes ipython/etc work as expected.
init_base_classes()
