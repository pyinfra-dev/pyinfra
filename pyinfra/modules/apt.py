# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

from pyinfra.api import op


@op
def repo(name, present=True):
    return []

@op
def packages(packages, present=True):
    return []
