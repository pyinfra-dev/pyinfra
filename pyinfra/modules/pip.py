from pyinfra.api import operation


@operation
def packages(packages=None, requirements_file=None, present=True, upgrade=False):
    return []
