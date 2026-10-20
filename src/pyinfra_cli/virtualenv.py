import os
import sys
from pathlib import Path

import click

from pyinfra import logger


def init_virtualenv() -> None:
    """
    Add a virtualenv to sys.path so the user can import modules from it.
    This isn't perfect: it doesn't use the Python interpreter with which the
    virtualenv was built, and it ignores the --no-site-packages option. A
    warning will appear suggesting the user installs IPython in the
    virtualenv, but for many cases, it probably works well enough.

    Adapted from IPython's implementation:
    https://github.com/ipython/ipython/blob/master/IPython/core/interactiveshell.py
    """

    if "VIRTUAL_ENV" not in os.environ:
        # Not in a virtualenv
        return

    p = Path(sys.executable)
    p_venv = Path(os.environ["VIRTUAL_ENV"])

    # executable path should end like /bin/python or \\scripts\\python.exe
    p_exe_up2 = p.parent.parent
    try:
        if p_exe_up2.samefile(p_venv):
            # Our exe is inside the virtualenv, don't need to do anything.
            return
    except OSError:
        pass

    # fallback venv detection:
    # stdlib venv may symlink sys.executable, so we can't use realpath.
    # but others can symlink *to* the venv Python, so we can't just use sys.executable.
    # So we just check every item in the symlink tree (generally <= 3)
    paths = [p]
    while p.is_symlink():
        target = p.readlink()
        p = target if target.is_absolute() else p.parent / target
        paths.append(p)

    p_venv_str = str(p_venv)
    # In Cygwin paths like 'c:\...' and '\cygdrive\c\...' are possible
    if p_venv_str.startswith("\\cygdrive"):
        p_venv_str = p_venv_str[11:]
    elif len(p_venv_str) >= 2 and p_venv_str[1] == ":":
        p_venv_str = p_venv_str[2:]

    if any(p_venv_str in str(candidate) for candidate in paths):
        # Running properly in the virtualenv, don't need to do anything
        return

    logger.warning(
        (
            "Attempting to work in a virtualenv.\n"
            "    If you encounter problems, please install pyinfra inside the virtualenv."
        ),
    )
    click.echo(err=True)

    if sys.platform == "win32":
        virtual_env = str(Path(os.environ["VIRTUAL_ENV"]) / "Lib" / "site-packages")
    else:
        virtual_env = str(
            Path(os.environ["VIRTUAL_ENV"])
            / "lib"
            / f"python{sys.version_info[0]}.{sys.version_info[1]}"
            / "site-packages"
        )

    import site

    sys.path.insert(0, virtual_env)
    site.addsitedir(virtual_env)
