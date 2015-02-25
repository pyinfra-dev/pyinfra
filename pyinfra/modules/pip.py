from pyinfra.api import operation


@operation
def packages(packages=None, requirements_file=None, present=True, upgrade=False):
    '''[Not implemented] Manage pip packages.'''
    packages = packages if isinstance(packages, list) else [packages]
    return []
