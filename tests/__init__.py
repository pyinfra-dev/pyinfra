# Import `pyinfra_cli` to trigger gevent monkey patching
import pyinfra_cli  # noqa: F401

import logging  # noqa: I100

import gevent.hub


logging.basicConfig(level=logging.DEBUG)

# Don't print out exceptions inside greenlets (because here we expect them!)
gevent.hub.Hub.NOT_ERROR = (Exception,)
