# pyinfra
# File: tests/__init__.py
# Desc: bootstrap basic logging for the tests

import logging

# This forces the import of all modules so coverage sees them
from pyinfra.modules import *  # noqa


logging.basicConfig(level=logging.DEBUG)
