import logging

import pyinfra_cli  # noqa: F401
from pyinfra import logger

logging.basicConfig(level=logging.DEBUG)
logger.setLevel(logging.DEBUG)
