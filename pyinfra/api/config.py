# pyinfra
# File: api/config.py
# Desc: the default config


class Config(object):
    state = None

    # % of hosts which have to fail for all operations to stop
    FAIL_PERCENT = None
    # Seconds to timeout SSH connections
    TIMEOUT = 10

    # Temporary directory (on the remote side) to use for caching any files/downloads
    TEMP_DIR = '/tmp/pyinfra'

    # All these can be overridden inside module calls
    SUDO = False
    SUDO_USER = None
    IGNORE_ERRORS = False

    def __init__(self, **kwargs):
        # Always apply some env
        env = kwargs.pop('env', {})
        self.ENV = env

        # Apply kwargs
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
