# pyinfra
# File: pyinfra/facts/util/packaging.py
# Desc: common functions for packaging facts

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

            packages[name] = matches.group(2)

    return packages
