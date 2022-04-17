import re


def parse_packages(regex, output):
    packages = {}

    for line in output:
        matches = re.match(regex, line)

        if matches:
            name = matches.group(1)
            packages.setdefault(name, set())
            packages[name].add(matches.group(2))

    return packages


def _parse_yum_or_zypper_repositories(output):
    repos = []

    current_repo = {}
    for line in output:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("["):
            if current_repo:
                repos.append(current_repo)
                current_repo = {}

            current_repo["name"] = line[1:-1]

        if current_repo and "=" in line:
            key, value = line.split("=", 1)
            current_repo[key] = value

    if current_repo:
        repos.append(current_repo)

    return repos


parse_yum_repositories = _parse_yum_or_zypper_repositories

parse_zypper_repositories = _parse_yum_or_zypper_repositories
