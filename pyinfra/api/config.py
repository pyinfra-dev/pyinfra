import six

from pyinfra import logger


class Config(object):
    '''
    The default/base configuration options for a pyinfra deploy.
    '''

    state = None

    # % of hosts which have to fail for all operations to stop
    FAIL_PERCENT = None

    # Seconds to timeout SSH connections
    CONNECT_TIMEOUT = 10

    # Temporary directory (on the remote side) to use for caching any files/downloads
    TEMP_DIR = '/tmp'

    # Gevent pool size (defaults to #of target hosts)
    PARALLEL = None

    # Specify a minimum required pyinfra version for a deploy
    MIN_PYINFRA_VERSION = None

    # All these can be overridden inside individual operation calls:

    # Switch to this user (from ssh_user) using su before executing operations
    SU_USER = None
    USE_SU_LOGIN = False

    # Use sudo and optional user
    SUDO = False
    SUDO_USER = None
    PRESERVE_SUDO_ENV = False
    USE_SUDO_LOGIN = False

    # Only show errors, but don't count as failure
    IGNORE_ERRORS = False

    # Shell to use to execute commands
    SHELL = 'sh'

    def __init__(self, **kwargs):
        # Always apply some env
        env = kwargs.pop('ENV', {})
        self.ENV = env

        # Replace TIMEOUT -> CONNECT_TIMEOUT
        if 'TIMEOUT' in kwargs:
            logger.warning((
                'Config.TIMEOUT is deprecated, '
                'please use Config.CONNECT_TIMEOUT instead'
            ))
            kwargs['CONNECT_TIMEOUT'] = kwargs.pop('TIMEOUT')

        # Apply kwargs
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)
