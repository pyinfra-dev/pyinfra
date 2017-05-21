import signal
import sys

import click

from colorama import init as colorama_init

from .legacy import run_main_with_legacy_arguments
from .main import cli, main


# Init colorama for Windows ANSI color support
colorama_init()

# Don't write out deploy.pyc/config.pyc etc
sys.dont_write_bytecode = True

# Make sure imported files (deploy.py/etc) behave as if imported from the cwd
sys.path.append('.')

# Shut it click
click.disable_unicode_literals_warning = True  # noqa


# Handle ctrl+c
def _signal_handler(signum, frame):
    print('Exiting upon user request!')
    sys.exit(0)

signal.signal(signal.SIGINT, _signal_handler)  # noqa


# TODO: Explain this!
if '-i' in sys.argv:
    run_main_with_legacy_arguments(main)
else:
    cli()
