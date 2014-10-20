from pyinfra.api import command


@command
def packages(packages=None, requirements_file=None, present=True, upgrade=False):
    return 'PIP, yo'
