from __future__ import unicode_literals

import six

from six import StringIO
from six.moves import shlex_quote
from six.moves.urllib.parse import urlparse

from pyinfra.facts.files import File


def _has_package(package, packages, expand_package_fact=None, match_any=False):
    def in_packages(pkg):
        if isinstance(pkg, list):
            return pkg[0] in packages and pkg[1] in packages[pkg[0]]
        return pkg in packages

    packages_to_check = [package]
    if expand_package_fact:
        packages_to_check = expand_package_fact(package) or packages_to_check

    checks = (in_packages(pkg) for pkg in packages_to_check)
    if match_any:
        return any(checks)
    return all(checks)


def ensure_packages(
    host, packages, current_packages, present,
    install_command, uninstall_command,
    latest=False, upgrade_command=None,
    version_join=None, lower=True,
    expand_package_fact=None,
):
    '''
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
        lower (bool): whether to lowercase package names
    '''

    if packages is None:
        return

    # Accept a single package as string
    if isinstance(packages, six.string_types):
        packages = [packages]

    # Lowercase packaging?
    if lower:
        packages = [
            package.lower()
            for package in packages
        ]

    # Version support?
    if version_join:
        # Split where versions present
        packages = [
            package.rsplit(version_join, 1)
            for package in packages
        ]

        # Covert to either string or list
        packages = [
            package[0] if len(package) == 1
            else package
            for package in packages
        ]

    # Diff the ensured packages against the remote state/fact
    diff_packages = []

    # Packages to upgrade? (install only)
    upgrade_packages = []

    # Installing?
    if present is True:
        for package in packages:
            # String version, just check if not existing
            if not _has_package(package, current_packages, expand_package_fact):
                diff_packages.append(package)

            else:
                # Present packages w/o version specified - for upgrade if latest
                if isinstance(package, six.string_types):
                    upgrade_packages.append(package)

                if not latest:
                    pkg_key = package[0] if isinstance(package, list) else package
                    if pkg_key in current_packages:
                        host.noop('package {0} is installed ({1})'.format(
                            package, ', '.join(current_packages[pkg_key]),
                        ))
                    else:
                        host.noop('package {0} is installed'.format(package))

    # Uninstalling?
    else:
        for package in packages:
            # String version, just check if existing
            if _has_package(package, current_packages, expand_package_fact, match_any=True):
                diff_packages.append(package)

            else:
                host.noop('package {0} is not installed'.format(package))

    # Convert packages back to string(/version)
    diff_packages = [
        version_join.join(package)
        if isinstance(package, list)
        else package
        for package in diff_packages
    ]

    if diff_packages:
        command = install_command if present else uninstall_command

        yield '{0} {1}'.format(
            command,
            ' '.join([shlex_quote(pkg) for pkg in diff_packages]),
        )

        for package in diff_packages:  # add/remove from current packages
            if present:
                version = 'unknown'
                if version_join:
                    bits = package.rsplit(version_join, 1)
                    package = bits[0]
                    if len(bits) == 2:
                        version = bits[1]
                current_packages[package] = [version]
            else:
                current_packages.pop(package, None)

    if latest and upgrade_command and upgrade_packages:
        yield '{0} {1}'.format(
            upgrade_command,
            ' '.join([shlex_quote(pkg) for pkg in upgrade_packages]),
        )


def ensure_rpm(state, host, files, source, present, package_manager_command):
    original_source = source

    # If source is a url
    if urlparse(source).scheme:
        # Generate a temp filename (with .rpm extension to please yum)
        temp_filename = '{0}.rpm'.format(state.get_temp_filename(source))

        # Ensure it's downloaded
        yield files.download(source, temp_filename, state=state, host=host)

        # Override the source with the downloaded file
        source = temp_filename

    # Check for file .rpm information
    info = host.fact.rpm_package(source)
    exists = False

    # We have info!
    if info:
        current_package = host.fact.rpm_package(info['name'])
        if current_package and current_package['version'] == info['version']:
            exists = True

    # Package does not exist and we want?
    if present and not exists:
        # If we had info, always install
        if info:
            yield 'rpm -i {0}'.format(source)

        # This happens if we download the package mid-deploy, so we have no info
        # but also don't know if it's installed. So check at runtime, otherwise
        # the install will fail.
        else:
            yield 'rpm -q `rpm -qp {0}` 2> /dev/null || rpm -i {0}'.format(source)

    # Package exists but we don't want?
    elif exists and not present:
        yield '{0} remove -y {1}'.format(package_manager_command, info['name'])

    else:
        host.noop('rpm {0} is {1}'.format(
            original_source,
            'installed' if present else 'not installed',
        ))


def ensure_yum_repo(
    state, host, files,
    name_or_url, baseurl, present, description, enabled, gpgcheck, gpgkey,
    repo_directory='/etc/yum.repos.d/',
    type_=None,
):
    url = None
    url_parts = urlparse(name_or_url)
    if url_parts.scheme:
        url = name_or_url
        name_or_url = url_parts.path.split('/')[-1]
        if name_or_url.endswith('.repo'):
            name_or_url = name_or_url[:-5]

    filename = '{0}{1}.repo'.format(repo_directory, name_or_url)

    # If we don't want the repo, just remove any existing file
    if not present:
        yield files.file(filename, present=False, state=state, host=host)
        return

    # If we're a URL, download the repo if it doesn't exist
    if url:
        if not host.get_fact(File, path=filename):
            yield files.download(url, filename, state=state, host=host)
        return

    # Description defaults to name
    description = description or name_or_url

    # Build the repo file from string
    repo_lines = [
        '[{0}]'.format(name_or_url),
        'name={0}'.format(description),
        'baseurl={0}'.format(baseurl),
        'enabled={0}'.format(1 if enabled else 0),
        'gpgcheck={0}'.format(1 if gpgcheck else 0),
    ]

    if type_:
        repo_lines.append('type={0}'.format(type_))

    if gpgkey:
        repo_lines.append('gpgkey={0}'.format(gpgkey))

    repo_lines.append('')
    repo = '\n'.join(repo_lines)
    repo = StringIO(repo)

    # Ensure this is the file on the server
    yield files.put(repo, filename, state=state, host=host)
