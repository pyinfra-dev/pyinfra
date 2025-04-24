# Import `pyinfra_cli` to trigger gevent monkey patching
import logging  # noqa: I100

import gevent.hub

import pyinfra_cli  # noqa: F401
from pyinfra import logger

logging.basicConfig(level=logging.DEBUG)
logger.setLevel(logging.DEBUG)

# Don't print out exceptions inside greenlets (because here we expect them!)
gevent.hub.Hub.NOT_ERROR = (Exception,)
