# pyinfra
# File: pyinfra/modules/venv.py
# Desc: virtualenv commands

from pyinfra.api import operation


@operation
def env(directory, present=True):
    return 'virtualenv create {0}'.format(directory)

# For use like: with venv.enter(dir)
class enter:
    def __init__(self, directory):
        self.directory = directory

    @operation
    def __enter__(self):
        return 'source {0}/bin/activate'.format(self.directory)

    @operation
    def __exit__(self, type, value, traceback):
        return 'deactivate'
