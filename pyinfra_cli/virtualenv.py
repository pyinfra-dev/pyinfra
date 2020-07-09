import os
import sys

import click

from pyinfra import logger


def init_virtualenv():
    '''
    Add a virtualenv to sys.path so the user can import modules from it.
    This isn't perfect: it doesn't use the Python interpreter with which the
    virtualenv was built, and it ignores the --no-site-packages option. A
    warning will appear suggesting the user installs IPython in the
    virtualenv, but for many cases, it probably works well enough.

    Adapted from IPython's implementation:
    https://github.com/ipython/ipython/blob/master/IPython/core/interactiveshell.py
    '''

    if 'VIRTUAL_ENV' not in os.environ:
        # Not in a virtualenv
        return

    p = os.path.normcase(sys.executable)
    p_venv = os.path.normcase(os.environ['VIRTUAL_ENV'])

    # executable path should end like /bin/python or \\scripts\\python.exe
    p_exe_up2 = os.path.dirname(os.path.dirname(p))
    if p_exe_up2 and os.path.samefile(p_exe_up2, p_venv):
        # Our exe is inside the virtualenv, don't need to do anything.
        return

    # fallback venv detection:
    # stdlib venv may symlink sys.executable, so we can't use realpath.
    # but others can symlink *to* the venv Python, so we can't just use sys.executable.
    # So we just check every item in the symlink tree (generally <= 3)
    paths = [p]
    while os.path.islink(p):
        p = os.path.normcase(os.path.join(os.path.dirname(p), os.readlink(p)))
        paths.append(p)

    # In Cygwin paths like 'c:\...' and '\cygdrive\c\...' are possible
    if p_venv.startswith('\\cygdrive'):
        p_venv = p_venv[11:]
    elif len(p_venv) >= 2 and p_venv[1] == ':':
        p_venv = p_venv[2:]

    if any(p_venv in p for p in paths):
        # Running properly in the virtualenv, don't need to do anything
        return

    logger.warning((
        'Attempting to work in a virtualenv.\n'
        '    If you encounter problems, please install pyinfra inside the virtualenv.'
    ))
    click.echo(err=True)

    if sys.platform == 'win32':
        virtual_env = os.path.join(
            os.environ['VIRTUAL_ENV'],
            'Lib',
            'site-packages',
        )
    else:
        virtual_env = os.path.join(
            os.environ['VIRTUAL_ENV'],
            'lib',
            'python%d.%d' % sys.version_info[:2],
            'site-packages',
        )

    import site
    sys.path.insert(0, virtual_env)
    site.addsitedir(virtual_env)
