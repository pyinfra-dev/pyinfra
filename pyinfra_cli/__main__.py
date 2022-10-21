import os
import signal
import sys

import click
import gevent

import pyinfra

from .main import cli

# Set CLI mode
pyinfra.is_cli = True

# Don't write out deploy.pyc/config.pyc etc
sys.dont_write_bytecode = True

# Shut it click
click.disable_unicode_literals_warning = True  # type: ignore

# Force line buffering
sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 1)
sys.stderr = os.fdopen(sys.stderr.fileno(), "w", 1)


def _handle_interrupt(signum, frame):
    click.echo("Exiting upon user request!")
    sys.exit(0)


try:
    # Kill any greenlets on ctrl+c
    gevent.signal_handler(signal.SIGINT, gevent.kill)
except AttributeError:
    # Legacy (gevent <1.2) support
    gevent.signal(signal.SIGINT, gevent.kill)

signal.signal(signal.SIGINT, _handle_interrupt)  # print the message and exit main


if __name__ == "pyinfra_cli.__main__":
    cli()
