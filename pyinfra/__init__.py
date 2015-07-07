# pyinfra
# File: pyinfra/__init__.py
# Desc: some global state for pyinfra

import logging


# Global pyinfra logger
logger = logging.getLogger('pyinfra')

# Builds facts index
from . import facts # noqa

from . import api # noqa
