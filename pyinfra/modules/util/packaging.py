from urllib.parse import urlparse


def ensure_packages(
    packages, current_packages, present,
    install_command, uninstall_command,
    latest=False, upgrade_command=None,
    version_join=None, lower=True,
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
    if isinstance(packages, str):
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
            # Tuple/version, check not in existing OR incorrect version
            if isinstance(package, list) and (
                package[0] not in current_packages
                or package[1] not in current_packages[package[0]]
            ):
                diff_packages.append(package)

            # String version, just check if not existing
            if isinstance(package, str) and package not in current_packages:
                diff_packages.append(package)

            # Present packages w/o version specified - for upgrade if latest
            if isinstance(package, str) and package in current_packages:
                upgrade_packages.append(package)

    # Uninstalling?
    else:
        for package in packages:
            # Tuple/version, heck existing AND correct version
            if isinstance(package, list) and (
                package[0] in current_packages
                and package[1] in current_packages[package[0]]
            ):
                diff_packages.append(package)

            # String version, just check if existing
            if isinstance(package, str) and package in current_packages:
                diff_packages.append(package)

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
            ' '.join(diff_packages),
        )

    if latest and upgrade_command and upgrade_packages:
        yield '{0} {1}'.format(
            upgrade_command,
            ' '.join(upgrade_packages),
        )


def ensure_rpm(state, host, files, source, present, package_manager_command):
    # If source is a url
    if urlparse(source).scheme:
        # Generate a temp filename (with .rpm extension to please yum)
        temp_filename = '{0}.rpm'.format(state.get_temp_filename(source))

        # Ensure it's downloaded
        yield files.download(state, host, source, temp_filename)

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
    if exists and not present:
        yield '{0} remove -y {1}'.format(package_manager_command, info['name'])
