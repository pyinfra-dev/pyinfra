# pyinfra
# File: pyinfra/modules/venv.py
# Desc: virtualenv commands

from pyinfra.api import command


@command
def env(directory, present=True):
    return 'virtualenv create {0}'.format(directory)

# For use like: with venv.enter(dir)
class enter:
    def __init__(self, directory):
        self.directory = directory

    @command
    def __enter__(self):
        return 'source {0}/bin/activate'.format(self.directory)

    @command
    def __exit__(self, type, value, traceback):
        return 'deactivate'
