from os import path

from pkg_resources import Requirement, ResolutionError, parse_version, require

from pyinfra import __version__, state

from .exceptions import PyinfraError


class ConfigDefaults:
    # % of hosts which have to fail for all operations to stop
    FAIL_PERCENT = None
    # Seconds to timeout SSH connections
    CONNECT_TIMEOUT = 10
    # Temporary directory (on the remote side) to use for caching any files/downloads
    TEMP_DIR = "/tmp"
    # Gevent pool size (defaults to #of target hosts)
    PARALLEL = 0
    # Specify the required pyinfra version (using PEP 440 setuptools specifier)
    REQUIRE_PYINFRA_VERSION = None
    # Specify any required packages (either using PEP 440 or a requirements file)
    # Note: this can also include pyinfra potentially replacing REQUIRE_PYINFRA_VERSION
    REQUIRE_PACKAGES = None
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
    # Use doas and optional user
    DOAS = False
    DOAS_USER = None
    # Only show errors but don't count as failure
    IGNORE_ERRORS = False
    # Shell to use to execute commands
    SHELL = "sh"


config_defaults = {key: value for key, value in ConfigDefaults.__dict__.items() if key.isupper()}


def check_pyinfra_version(version: str):
    if not version:
        return

    running_version = parse_version(__version__)
    required_versions = Requirement.parse(
        "pyinfra{0}".format(version),
    )

    if running_version not in required_versions:
        raise PyinfraError(
            ("pyinfra version requirement not met " "(requires {0}, running {1})").format(
                version,
                __version__,
            ),
        )


def check_require_packages(requirements_config):
    if not requirements_config:
        return

    if isinstance(requirements_config, (list, tuple)):
        requirements = requirements_config
    else:
        with open(path.join(state.cwd, requirements_config), encoding="utf-8") as f:
            requirements = [line.split("#egg=")[-1] for line in f.read().splitlines()]

    try:
        require(requirements)
    except ResolutionError as e:
        raise PyinfraError(
            "Deploy requirements ({0}) not met: {1}".format(
                requirements_config,
                e,
            ),
        )


config_checkers = {
    "REQUIRE_PYINFRA_VERSION": check_pyinfra_version,
    "REQUIRE_PACKAGES": check_require_packages,
}


class Config(ConfigDefaults):
    """
    The default/base configuration options for a pyinfra deploy.
    """

    def __init__(self, **kwargs):
        # Always apply some env
        env = kwargs.pop("ENV", {})
        self.ENV = env

        config = config_defaults.copy()
        config.update(kwargs)

        for key, value in config.items():
            setattr(self, key, value)

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

        checker = config_checkers.get(key)
        if checker:
            checker(value)

    def get_current_state(self):
        return [(key, getattr(self, key)) for key in config_defaults.keys()]

    def set_current_state(self, config_state):
        for key, value in config_state:
            setattr(self, key, value)

    def lock_current_state(self):
        self._locked_config = self.get_current_state()

    def reset_locked_state(self):
        self.set_current_state(self._locked_config)

    def copy(self) -> "Config":
        return Config(**dict(self.get_current_state()))
