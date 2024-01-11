from os import path
from typing import Optional

# TODO: move to importlib.resources
from pkg_resources import Requirement, ResolutionError, parse_version, require

from pyinfra import __version__, state

from .exceptions import PyinfraError


class ConfigDefaults:
    # % of hosts which have to fail for all operations to stop
    FAIL_PERCENT: Optional[int] = None
    # Seconds to timeout SSH connections
    CONNECT_TIMEOUT: int = 10
    # Temporary directory (on the remote side) to use for caching any files/downloads, the default
    # None value first tries to load the hosts' temporary directory configured via "TMPDIR" env
    # variable, falling back to DEFAULT_TEMP_DIR if not set.
    TEMP_DIR: Optional[str] = None
    DEFAULT_TEMP_DIR: str = "/tmp"
    # Gevent pool size (defaults to #of target hosts)
    PARALLEL: int = 0
    # Specify the required pyinfra version (using PEP 440 setuptools specifier)
    REQUIRE_PYINFRA_VERSION: Optional[str] = None
    # Specify any required packages (either using PEP 440 or a requirements file)
    # Note: this can also include pyinfra potentially replacing REQUIRE_PYINFRA_VERSION
    REQUIRE_PACKAGES: Optional[str] = None
    # All these can be overridden inside individual operation calls:
    # Switch to this user (from ssh_user) using su before executing operations
    SU_USER: Optional[str] = None
    USE_SU_LOGIN: bool = False
    SU_SHELL: bool = False
    PRESERVE_SU_ENV: bool = False
    # Use sudo and optional user
    SUDO: bool = False
    SUDO_USER: Optional[str] = None
    PRESERVE_SUDO_ENV: bool = False
    USE_SUDO_LOGIN: bool = False
    SUDO_PASSWORD: Optional[str] = None
    # Use doas and optional user
    DOAS: bool = False
    DOAS_USER: Optional[str] = None
    # Only show errors but don't count as failure
    IGNORE_ERRORS: bool = False
    # Shell to use to execute commands
    SHELL: str = "sh"


config_defaults = {key: value for key, value in ConfigDefaults.__dict__.items() if key.isupper()}


def check_pyinfra_version(version: str):
    if not version:
        return
    running_version = parse_version(__version__)
    required_versions = Requirement.parse("pyinfra{0}".format(version))

    if running_version not in required_versions:  # type: ignore[operator]
        raise PyinfraError(
            f"pyinfra version requirement not met (requires {version}, running {__version__})"
        )


def check_require_packages(requirements_config):
    if not requirements_config:
        return

    if isinstance(requirements_config, (list, tuple)):
        requirements = requirements_config
    else:
        with open(path.join(state.cwd or "", requirements_config), encoding="utf-8") as f:
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
