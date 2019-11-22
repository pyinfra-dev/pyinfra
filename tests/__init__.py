import logging

import gevent.hub


logging.basicConfig(level=logging.DEBUG)

# Don't print out exceptions inside greenlets (because here we expect them!)
gevent.hub.Hub.NOT_ERROR = (Exception,)
