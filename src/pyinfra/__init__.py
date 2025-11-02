"""
Welcome to pyinfra.
"""

import logging

# Global flag set True by `pyinfra_cli.__main__`
is_cli = False

# Global pyinfra logger
logger = logging.getLogger("pyinfra")

# Trigger context module creation
from .context import config, host, init_base_classes, inventory, state  # noqa

# Setup package level version
from .version import __version__  # noqa

# Initialise base classes - this sets the context modules to point at the underlying
# class objects (Host, etc), which makes ipython/etc work as expected.
init_base_classes()
