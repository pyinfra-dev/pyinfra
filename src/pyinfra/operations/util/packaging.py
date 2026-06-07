from __future__ import annotations

from collections import defaultdict
from io import StringIO
from typing import NamedTuple, cast
from collections.abc import Callable
from urllib.parse import urlparse

from packaging.requirements import InvalidRequirement, Requirement

from pyinfra import logger
from pyinfra.api import Host, OperationValueError, State
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.facts.files import File
from pyinfra.facts.rpm import RpmPackage
from pyinfra.facts.util.packages import PackageInfo, PackageStatus
from pyinfra.operations import files


def default_inst_vers_format_fn(name: str, operator: str, version: str):
    return f"{name}{operator}{version}"


class PkgInfo(NamedTuple):
    name: str
    version: str
    operator: str
    url: str
    inst_vers_format_fn: Callable = default_inst_vers_format_fn
    """
    The key packaging information needed: version, operator and url are optional.
    """

    @property
    def lkup_name(self) -> str | list[str]:
        return self.name if self.version == "" else [self.name, self.version]

    @property
    def has_version(self) -> bool:
        return self.version != ""

    @property
    def inst_vers(self) -> str:
        """String that represents how a program can be installed.

        - If self.url exists, then url is always returned.
        - If self.version exists, then inst_vers_format_fn is used
        to create the string. The default template is '{name}{operator}{version}'.
        - Otherwise, self.name is returned.

        Note, the result string will be quoted, so input is shell safe.
        """

        if self.url:
            return StringCommand(QuoteString(self.url)).get_raw_value()

        if self.version:
            return StringCommand(
                QuoteString(self.inst_vers_format_fn(self.name, self.operator, self.version))
            ).get_raw_value()
        return StringCommand(QuoteString(self.name)).get_raw_value()

    @classmethod
    def from_possible_pair(cls, s: str, join: str | None) -> PkgInfo:
        if join is not None:
            pieces = s.rsplit(join, 1)
            return cls(pieces[0], pieces[1] if len(pieces) > 1 else "", join, "")

        return cls(s, "", "", "")

    @classmethod
    def from_pep508(cls, s: str) -> PkgInfo | None:
        """
        Separate out the useful parts (name, url, operator, version) of a PEP-508 dependency.
        Note: only one specifier is allowed.
        PEP-0426 states that Python packages should be compared using lowercase; thus
        the name is lower-cased
        For backwards compatibility, invalid requirements are assumed to be package names with a
        warning that this will change in the next major release
        """
        pep_508 = "PEP 508 non-compliant "
        treatment = "requirement treated as package name"
        will_change = "4.x will make this an error"  # pip and pipx already throw away None's
        try:
            reqt = Requirement(s)
        except InvalidRequirement as e:
            logger.warning(f"{pep_508} :{e}\n{will_change}")
            return cls(s, "", "", "")
        else:
            if (len(reqt.specifier) > 0) and (len(reqt.specifier) > 1):
                logger.warning(f"{pep_508}/unsupported specifier ({s}) {treatment}\n{will_change}")
                return cls(s, "", "", "")
            else:
                spec = next(iter(reqt.specifier), None)
                return cls(
                    reqt.name.lower(),
                    spec.version if spec is not None else "",
                    spec.operator if spec is not None else "",
                    reqt.url or "",
                )


def _has_package(
    package: str | list[str],
    packages: dict[str, set[str]] | dict[str, PackageInfo],
    expand_package_fact: Callable[[str], list[str | list[str]]] | None = None,
    match_any=False,
) -> tuple[bool, dict]:
    def in_packages(pkg_name, pkg_versions):
        if pkg_name not in packages:
            return False
        value = packages[pkg_name]
        if isinstance(value, PackageInfo):
            if not pkg_versions:
                return True
            return any(version in value.installed_versions for version in pkg_versions)
        if not pkg_versions:
            return True
        return any(version in value for version in pkg_versions)

    packages_to_check: list[str | list[str]] = [package]
    if expand_package_fact:
        if isinstance(package, list):
            packages_to_check = expand_package_fact(package[0]) or packages_to_check
        else:
            packages_to_check = expand_package_fact(package) or packages_to_check

    package_name_to_versions = defaultdict(set)
    for pkg in packages_to_check:
        if isinstance(pkg, list):
            package_name_to_versions[pkg[0]].add(pkg[1])
        else:
            package_name_to_versions[pkg]  # just make sure it exists

    checks = (
        in_packages(pkg_name, pkg_versions)
        for pkg_name, pkg_versions in package_name_to_versions.items()
    )

    if match_any:
        return any(checks), package_name_to_versions
    return all(checks), package_name_to_versions


def _get_package_status(
    current_packages: dict[str, set[str]] | dict[str, PackageInfo],
    pkg_name: str,
) -> PackageStatus | None:
    """Return the PackageStatus for ``pkg_name``, or ``None`` for old-format dicts."""
    if pkg_name not in current_packages:
        return None
    value = current_packages[pkg_name]
    if isinstance(value, PackageInfo):
        return value.status
    return None


def _format_version(
    current_packages: dict[str, set[str]] | dict[str, PackageInfo],
    pkg_name: str,
) -> str:
    """Return a human-readable version string for noop messages.

    For the legacy ``set[str]`` shape, multiple versions are sorted so the
    noop output is deterministic across runs. For :class:`PackageInfo`,
    ``installed_versions`` is already sorted by ``build_package_map``.
    """
    if pkg_name not in current_packages:
        return ""
    value = current_packages[pkg_name]
    if isinstance(value, PackageInfo):
        return ",".join(value.installed_versions)
    return ",".join(sorted(value))


def ensure_packages(
    host: Host,
    packages_to_ensure: str | list[str] | list[PkgInfo] | None,
    current_packages: dict[str, set[str]] | dict[str, PackageInfo],
    present: bool,
    install_command: str | StringCommand,
    uninstall_command: str | StringCommand,
    latest: bool = False,
    upgrade_command: str | StringCommand | None = None,
    version_join: str | None = None,
    expand_package_fact: Callable[[str], list[str | list[str]]] | None = None,
    expand_match_any: bool = False,
):
    """
    Handles this common scenario:

    + We have a list of packages(/versions/urls) to ensure
    + We have a map of existing package -> versions (old) or PackageInfo (new)
    + We have the common command bits (install, uninstall, version "joiner")
    + Outputs commands to ensure our desired packages/versions
    + Optionally upgrades packages w/o specified version when present

    When ``current_packages`` values are :class:`PackageInfo` objects, the richer
    status information is used:

    * **HELD** packages always produce a noop, even when ``latest=True``.
    * **UPGRADEABLE** packages are upgraded when ``latest=True``.
    * **INSTALLED** packages with no available upgrade produce a noop.

    With the legacy ``dict[str, set[str]]`` format, behaviour is unchanged:
    ``latest=True`` blindly adds every versionless package to the upgrade list.

    Args:
        packages_to_ensure (list): list of packages or package/versions or PkgInfo's
        current_packages (dict): dict of package names -> version, or name -> PackageInfo
        present (bool): whether packages should exist or not
        install_command (str): command to prefix to list of packages to install
        uninstall_command (str): as above for uninstalling packages
        latest (bool): whether to upgrade installed packages when present
        upgrade_command (str): as above for upgrading
        version_join (str): the package manager specific "joiner", ie ``=`` for \
            ``<apt_pkg>=<version>``.  Not allowed if (pkg, ver, url) tuples are provided.
        expand_package_fact: fact returning packages providing a capability \
            (ie ``yum whatprovides``)
    """

    if packages_to_ensure is None:
        return
    if isinstance(packages_to_ensure, str):
        packages_to_ensure = [packages_to_ensure]
    if len(packages_to_ensure) == 0:
        return

    packages: list[PkgInfo] = []
    if isinstance(packages_to_ensure[0], PkgInfo):
        packages = cast("list[PkgInfo]", packages_to_ensure)
        if version_join is not None:
            raise OperationValueError("cannot specify version_join and provide list[PkgInfo]")
    else:
        packages = [
            PkgInfo.from_possible_pair(package, version_join)
            for package in cast("list[str]", packages_to_ensure)
        ]

    diff_packages = []
    diff_expanded_packages = {}

    upgrade_packages = []

    if present is True:
        for package in packages:
            has_package, expanded_packages = _has_package(
                package.lkup_name, current_packages, expand_package_fact, match_any=expand_match_any
            )

            if not has_package:
                diff_packages.append(package.inst_vers)
                diff_expanded_packages[package.name] = expanded_packages
            else:
                pkg_name = package.name
                status = _get_package_status(current_packages, pkg_name)

                if status == PackageStatus.HELD:
                    host.noop(f"package {pkg_name} is held")
                    continue

                # Present packages w/o version specified: candidate for upgrade
                if not package.has_version:
                    if status == PackageStatus.UPGRADEABLE:
                        upgrade_packages.append(package.inst_vers)
                    elif latest and status is None:
                        # Old format: try all (backward compat)
                        upgrade_packages.append(package.inst_vers)

                if not latest:
                    version_display = _format_version(current_packages, pkg_name)
                    if version_display:
                        host.noop(f"package {pkg_name} is installed ({version_display})")
                    else:
                        host.noop(f"package {pkg_name} is installed")
                elif status == PackageStatus.INSTALLED:
                    version_display = _format_version(current_packages, pkg_name)
                    if version_display:
                        host.noop(f"package {pkg_name} is up to date ({version_display})")
                    else:
                        host.noop(f"package {pkg_name} is up to date")
    if present is False:
        for package in packages:
            has_package, expanded_packages = _has_package(
                package.lkup_name, current_packages, expand_package_fact, match_any=True
            )

            if has_package:
                diff_packages.append(package.inst_vers)
                diff_expanded_packages[package.name] = expanded_packages
            else:
                host.noop(f"package {package.name} is not installed")

    if diff_packages:
        command = install_command if present else uninstall_command
        yield f"{command} {' '.join([pkg for pkg in diff_packages])}"

    if latest and upgrade_command and upgrade_packages:
        yield f"{upgrade_command} {' '.join([pkg for pkg in upgrade_packages])}"


def ensure_rpm(state: State, host: Host, source: str, present: bool, package_manager_command: str):
    original_source = source

    # If source is a url
    if urlparse(source).scheme:
        # Generate a temp filename (with .rpm extension to please yum)
        temp_filename = f"{host.get_temp_filename(source)}.rpm"

        # Ensure it's downloaded
        yield from files.download._inner(src=source, dest=temp_filename)

        # Override the source with the downloaded file
        source = temp_filename

    # Check for file .rpm information
    info = host.get_fact(RpmPackage, package=source)
    exists = False

    # We have info!
    if info:
        current_package = host.get_fact(RpmPackage, package=info["name"])
        if current_package and current_package["version"] == info["version"]:
            exists = True

    # Package does not exist and we want?
    if present and not exists:
        # If we had info, always install
        if info:
            yield f"rpm -i {source}"
        # This happens if we download the package mid-deploy, so we have no info
        # but also don't know if it's installed. So check at runtime, otherwise
        # the install will fail.
        else:
            yield f"rpm -q `rpm -qp {source}` 2> /dev/null || rpm -i {source}"

    # Package exists but we don't want?
    elif exists and not present:
        yield f"{package_manager_command} remove -y {info['name']}"
    else:
        host.noop(
            f"rpm {original_source} is {'installed' if present else 'not installed'}",
        )


def ensure_yum_repo(
    host: Host,
    name_or_url: str,
    baseurl: str | None,
    present: bool,
    description: str | None,
    enabled: bool,
    gpgcheck: bool,
    gpgkey: str | None,
    repo_directory="/etc/yum.repos.d/",
    type_: str | None = None,
):
    url = None
    url_parts = urlparse(name_or_url)
    if url_parts.scheme:
        url = name_or_url
        name_or_url = url_parts.path.split("/")[-1]
        if name_or_url.endswith(".repo"):
            name_or_url = name_or_url[:-5]

    filename = f"{repo_directory}{name_or_url}.repo"

    # If we don't want the repo, just remove any existing file
    if not present:
        yield from files.file._inner(path=filename, present=False)
        return

    # If we're a URL, download the repo if it doesn't exist
    if url:
        if not host.get_fact(File, path=filename):
            yield from files.download._inner(src=url, dest=filename)
        return

    assert isinstance(baseurl, str)

    # Description defaults to name
    description = description or name_or_url

    # Build the repo file from string
    repo_lines = [
        f"[{name_or_url}]",
        f"name={description}",
        f"baseurl={baseurl}",
        f"enabled={1 if enabled else 0}",
        f"gpgcheck={1 if gpgcheck else 0}",
    ]

    if type_:
        repo_lines.append(f"type={type_}")

    if gpgkey:
        repo_lines.append(f"gpgkey={gpgkey}")

    repo_lines.append("")
    repo = "\n".join(repo_lines)
    repo_file = StringIO(repo)

    # Ensure this is the file on the server
    yield from files.put._inner(src=repo_file, dest=filename)
