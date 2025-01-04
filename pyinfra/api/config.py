try:
    import importlib_metadata
except ImportError:
    import importlib.metadata as importlib_metadata  # type: ignore[no-redef]

from os import path
from typing import Iterable, Optional, Set

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from typing_extensions import override

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
    running_version = Version(__version__)
    required_versions = SpecifierSet(version)

    if running_version not in required_versions:
        raise PyinfraError(
            f"pyinfra version requirement not met (requires {version}, running {__version__})"
        )


def _check_requirements(requirements: Iterable[str]) -> Set[Requirement]:
    """
    Check whether each of the given requirements and all their dependencies are
    installed.

    Or more precisely, this checks that each of the given *requirements* is
    satisfied by some installed *distribution package*, and so on recursively
    for each of the dependencies of those distribution packages. The terminology
    here is as follows:

    * A *distribution package* is essentially a thing that can be installed with
      ``pip``, from an sdist or wheel or Git repo or so on.
    * A *requirement* is the expectation that a distribution package satisfying
      some constraint is installed.
    * A *dependency* is a requirement specified by a distribution package (as
      opposed to the requirements passed in to this function).

    So what this function does is start from the given requirements, for each
    one check that it is satisfied by some installed distribution package, and
    if so recursively perform the same check on all the dependencies of that
    distribution package. In short, it's traversing the graph of package
    requirements. It stops whenever it finds a requirement that is not satisfied
    (i.e. a required package that is not installed), or when it runs out of
    requirements to check.

    .. note::
        This is basically equivalent to ``pkg_resources.require()`` except that
        when ``require()`` succeeds, it will return the list of distribution
        packages that satisfy the given requirements and their dependencies, and
        when it fails, it will raise an exception. This function just returns
        the requirements which were not satisfied instead.

    :param requirements: The requirements to check for in the set of installed
        packages (along with their dependencies).
    :return: The set of requirements that were not satisfied, which will be
        an empty set if all requirements (recursively) were satisfied.
    """

    # Based on pkg_resources.require() from setuptools. The implementation of
    # hbutils.system.check_reqs() from the hbutils package was also helpful in
    # clarifying what this is supposed to do.

    reqs_to_check: Set[Requirement] = set(Requirement(r) for r in requirements)
    reqs_satisfied: Set[Requirement] = set()
    reqs_not_satisfied: Set[Requirement] = set()

    while reqs_to_check:
        req = reqs_to_check.pop()
        assert req not in reqs_satisfied and req not in reqs_not_satisfied

        # Check for an installed distribution package with the right name and version
        try:
            dist = importlib_metadata.distribution(req.name)
        except importlib_metadata.PackageNotFoundError:
            # No installed package with the right name
            # This would raise a DistributionNotFound error from pkg_resources.require()
            reqs_not_satisfied.add(req)
            continue

        if dist.version not in req.specifier:
            # There is a distribution with the right name but wrong version
            # This would raise a VersionConflict error from pkg_resources.require()
            reqs_not_satisfied.add(req)
            continue

        reqs_satisfied.add(req)

        # If the distribution package has dependencies of its own, go through
        # those dependencies and for each one add it to the set to be checked if
        # - it's unconditional (no marker)
        # - or it's conditional and the condition is satisfied (the marker
        #   evaluates to true) in the current environment
        # Markers can check things like the Python version and system version
        # etc., and/or they can check which extras of the distribution package
        # were required. To facilitate checking extras we have to pass the extra
        # in the environment when calling Marker.evaluate().
        if dist.requires:
            if req.extras:
                extras_envs = [{"extra": extra} for extra in req.extras]

                def evaluate_marker(marker: Marker) -> bool:
                    return any(map(marker.evaluate, extras_envs))

            else:

                def evaluate_marker(marker: Marker) -> bool:
                    return marker.evaluate()

            for dist_req_str in dist.requires:
                dist_req = Requirement(dist_req_str)
                if dist_req in reqs_satisfied or dist_req in reqs_not_satisfied:
                    continue
                if (not dist_req.marker) or evaluate_marker(dist_req.marker):
                    reqs_to_check.add(dist_req)

    return reqs_not_satisfied


def check_require_packages(requirements_config):
    if not requirements_config:
        return

    if isinstance(requirements_config, (list, tuple)):
        requirements = requirements_config
    else:
        with open(path.join(state.cwd or "", requirements_config), encoding="utf-8") as f:
            requirements = [line.split("#egg=")[-1] for line in f.read().splitlines()]

    requirements_not_met = _check_requirements(requirements)
    if requirements_not_met:
        raise PyinfraError(
            "Deploy requirements ({0}) not met: missing {1}".format(
                requirements_config, ", ".join(str(r) for r in requirements_not_met)
            )
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

    @override
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

    def lock_current_state(self) -> None:
        self._locked_config = self.get_current_state()

    def reset_locked_state(self) -> None:
        self.set_current_state(self._locked_config)

    def copy(self) -> "Config":
        return Config(**dict(self.get_current_state()))
