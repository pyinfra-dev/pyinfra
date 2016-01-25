# pyinfra
# File: pyinfra/modules/util/packaging.py
# Desc: common functions for packaging modules


def ensure_packages(
    packages, current_packages, present,
    install_command, uninstall_command, lower=True
):
    if packages is None:
        return

    # Accept a single package as string
    if isinstance(packages, basestring):
        packages = [packages]

    # Lowercase packaging?
    if lower:
        packages = [
            package.lower()
            for package in packages
        ]

    # Current packages not strictly required
    if not current_packages:
        current_packages = {}

    commands = []

    # Installing?
    if present is True:
        diff_packages = [
            package for package in packages
            if package not in current_packages
        ]

        if diff_packages:
            commands.append('{0} {1}'.format(
                install_command,
                ' '.join(diff_packages)
            ))

    # Uninstalling?
    else:
        diff_packages = [
            package for package in packages
            if package in current_packages
        ]

        if diff_packages:
            commands.append('{0} {1}'.format(
                uninstall_command,
                ' '.join(diff_packages)
            ))

    return commands
