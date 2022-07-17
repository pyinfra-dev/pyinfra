import shlex
from collections import defaultdict
from io import StringIO
from urllib.parse import urlparse

from pyinfra.facts.files import File
from pyinfra.facts.rpm import RpmPackage


def _package_name(package):
    if isinstance(package, list):
        return package[0]
    return package


def _has_package(package, packages, expand_package_fact=None, match_any=False):
    def in_packages(pkg_name, pkg_versions):
        if not pkg_versions:
            return pkg_name in packages
        return pkg_name in packages and any(
            version in packages[pkg_name] for version in pkg_versions
        )

    packages_to_check = [package]
    if expand_package_fact:
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


def ensure_packages(
    host,
    packages,
    current_packages,
    present,
    install_command,
    uninstall_command,
    latest=False,
    upgrade_command=None,
    version_join=None,
    expand_package_fact=None,
):
    """
    Handles this common scenario:

    + We have a list of packages(/versions) to ensure
    + We have a map of existing package -> versions
    + We have the common command bits (install, uninstall, version "joiner")
    + Outputs commands to ensure our desired packages/versions
    + Optionally upgrades packages w/o specified version when present

    Args:
        packages (list): list of packages or package/versions
        current_packages (fact): fact returning dict of package names -> version
        present (bool): whether packages should exist or not
        install_command (str): command to prefix to list of packages to install
        uninstall_command (str): as above for uninstalling packages
        latest (bool): whether to upgrade installed packages when present
        upgrade_command (str): as above for upgrading
        version_join (str): the package manager specific "joiner", ie ``=`` for \
            ``<apt_pkg>=<version>``
    """

    if packages is None:
        return

    if isinstance(packages, str):
        packages = [packages]

    if version_join:
        packages = [
            package[0] if len(package) == 1 else package
            for package in [package.rsplit(version_join, 1) for package in packages]
        ]

    diff_packages = []
    diff_expanded_packages = {}

    upgrade_packages = []

    if present is True:
        for package in packages:
            has_package, expanded_packages = _has_package(
                package,
                current_packages,
                expand_package_fact,
            )

            if not has_package:
                diff_packages.append(package)
                diff_expanded_packages[_package_name(package)] = expanded_packages
            else:
                # Present packages w/o version specified - for upgrade if latest
                if isinstance(package, str):
                    upgrade_packages.append(package)

                if not latest:
                    pkg_name = _package_name(package)
                    if pkg_name in current_packages:
                        host.noop(
                            "package {0} is installed ({1})".format(
                                package,
                                ", ".join(current_packages[pkg_name]),
                            ),
                        )
                    else:
                        host.noop("package {0} is installed".format(package))

    if present is False:
        for package in packages:
            # String version, just check if existing
            has_package, expanded_packages = _has_package(
                package,
                current_packages,
                expand_package_fact,
                match_any=True,
            )

            if has_package:
                diff_packages.append(package)
                diff_expanded_packages[_package_name(package)] = expanded_packages
            else:
                host.noop("package {0} is not installed".format(package))

    if diff_packages:
        command = install_command if present else uninstall_command

        joined_packages = [
            version_join.join(package) if isinstance(package, list) else package
            for package in diff_packages
        ]

        yield "{0} {1}".format(
            command,
            " ".join([shlex.quote(pkg) for pkg in joined_packages]),
        )

        for package in diff_packages:  # add/remove from current packages
            pkg_name = _package_name(package)
            version = "unknown"
            if isinstance(package, list):
                version = package[1]

            if present:
                current_packages[pkg_name] = [version]
                current_packages.update(diff_expanded_packages.get(pkg_name, {}))
            else:
                current_packages.pop(pkg_name, None)
                for name in diff_expanded_packages.get(pkg_name, {}):
                    current_packages.pop(name, None)

    if latest and upgrade_command and upgrade_packages:
        yield "{0} {1}".format(
            upgrade_command,
            " ".join([shlex.quote(pkg) for pkg in upgrade_packages]),
        )


def ensure_rpm(state, host, files, source, present, package_manager_command):
    original_source = source

    # If source is a url
    if urlparse(source).scheme:
        # Generate a temp filename (with .rpm extension to please yum)
        temp_filename = "{0}.rpm".format(state.get_temp_filename(source))

        # Ensure it's downloaded
        yield from files.download(source, temp_filename)

        # Override the source with the downloaded file
        source = temp_filename

    # Check for file .rpm information
    info = host.get_fact(RpmPackage, name=source)
    exists = False

    # We have info!
    if info:
        current_package = host.get_fact(RpmPackage, name=info["name"])
        if current_package and current_package["version"] == info["version"]:
            exists = True

    # Package does not exist and we want?
    if present and not exists:
        # If we had info, always install
        if info:
            yield "rpm -i {0}".format(source)
            host.create_fact(RpmPackage, kwargs={"name": info["name"]}, data=info)

        # This happens if we download the package mid-deploy, so we have no info
        # but also don't know if it's installed. So check at runtime, otherwise
        # the install will fail.
        else:
            yield "rpm -q `rpm -qp {0}` 2> /dev/null || rpm -i {0}".format(source)

    # Package exists but we don't want?
    elif exists and not present:
        yield "{0} remove -y {1}".format(package_manager_command, info["name"])
        host.delete_fact(RpmPackage, kwargs={"name": info["name"]})

    else:
        host.noop(
            "rpm {0} is {1}".format(
                original_source,
                "installed" if present else "not installed",
            ),
        )


def ensure_yum_repo(
    state,
    host,
    files,
    name_or_url,
    baseurl,
    present,
    description,
    enabled,
    gpgcheck,
    gpgkey,
    repo_directory="/etc/yum.repos.d/",
    type_=None,
):
    url = None
    url_parts = urlparse(name_or_url)
    if url_parts.scheme:
        url = name_or_url
        name_or_url = url_parts.path.split("/")[-1]
        if name_or_url.endswith(".repo"):
            name_or_url = name_or_url[:-5]

    filename = "{0}{1}.repo".format(repo_directory, name_or_url)

    # If we don't want the repo, just remove any existing file
    if not present:
        yield from files.file(filename, present=False)
        return

    # If we're a URL, download the repo if it doesn't exist
    if url:
        if not host.get_fact(File, path=filename):
            yield from files.download(url, filename)
        return

    # Description defaults to name
    description = description or name_or_url

    # Build the repo file from string
    repo_lines = [
        "[{0}]".format(name_or_url),
        "name={0}".format(description),
        "baseurl={0}".format(baseurl),
        "enabled={0}".format(1 if enabled else 0),
        "gpgcheck={0}".format(1 if gpgcheck else 0),
    ]

    if type_:
        repo_lines.append("type={0}".format(type_))

    if gpgkey:
        repo_lines.append("gpgkey={0}".format(gpgkey))

    repo_lines.append("")
    repo = "\n".join(repo_lines)
    repo = StringIO(repo)

    # Ensure this is the file on the server
    yield from files.put(repo, filename)
