# pyinfra
# File: pyinfra/modules/linux.py
# Desc: the base Linux module

from pyinfra.api import command, server


@command
def user(name, present=True, home='/home/{0}', shell='/bin/bash', public_keys=None, delete_keys=False):
    commands = []
    is_present = name in server.fact('Users')

    def _do_keys():
        pass

    # User exists but we don't want them?
    if is_present and not present:
        commands += 'userdel {0}'.format(name)

    # User doesn't exist but we want them?
    elif not is_present and present:
        # Create the user w/home/shell
        # Add SSH keys
        _do_keys()

    # User exists and we want them, check home/shell/keys
    else:
        # Check homedir
        # Check shell
        # Add SSH keys
        _do_keys()

    return commands

@command
def file(name, present=True, owner=None, group=None, permissions=None):
    return 'chmod BLAH'

@command
def directory(name, present=True, owner=None, group=None, permissions=None):
    return 'chmod BLAH'

@command
def service(name, running=True, restarted=False):
    pass
