# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

from pyinfra.api import command


@command
def repo(name, present=True):
    return 'REPO'

@command
def packages(packages, present=True):
    return ['PACKAGES', True]
