import re


def parse_packages(regex, output, lower=True):
    packages = {}

    for line in output:
        matches = re.match(regex, line)

        if matches:
            # Sort out name
            name = matches.group(1)
            if lower:
                name = name.lower()

            packages.setdefault(name, set())
            packages[name].add(matches.group(2))

    return packages


def parse_yum_repositories(output):
    repos = []

    current_repo = {}
    for line in output:
        line = line.strip()
        if not line:
            continue

        if line.startswith('['):
            if current_repo:
                repos.append(current_repo)
                current_repo = {}

            current_repo['name'] = line[1:-1]

        if current_repo and '=' in line:
            key, value = line.split('=', 1)
            current_repo[key] = value

    if current_repo:
        repos.append(current_repo)

    return repos
