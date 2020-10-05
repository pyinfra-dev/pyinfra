import six


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

    # Specify the required pyinfra version (using PEP 440 setuptools specifier)
    REQUIRE_PYINFRA_VERSION = None
    # Specify any required packages (either using PEP 440 or a requirements file)
    # Note: this can also include pyinfra, potentially replacing REQUIRE_PYINFRA_VERSION
    REQUIRE_PACKAGES = None

    # COMPAT w/<1.1
    # TODO: remove this in favour of above at v2
    # Specify a minimum required pyinfra version for a deploy
    MIN_PYINFRA_VERSION = None

    # All these can be overridden inside individual operation calls:

    # Switch to this user (from ssh_user) using su before executing operations
    SU_USER = None
    USE_SU_LOGIN = False
    SU_SHELL = None
    PRESERVE_SU_ENV = False

    # Use sudo and optional user
    SUDO = False
    SUDO_USER = None
    PRESERVE_SUDO_ENV = False
    USE_SUDO_LOGIN = False
    USE_SUDO_PASSWORD = False

    # Only show errors, but don't count as failure
    IGNORE_ERRORS = False

    # Shell to use to execute commands
    SHELL = None

    def __init__(self, **kwargs):
        # Always apply some env
        env = kwargs.pop('ENV', {})
        self.ENV = env

        # Apply kwargs
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)
