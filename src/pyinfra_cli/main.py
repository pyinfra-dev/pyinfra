import signal
import sys

import gevent

import pyinfra
from pyinfra.api.output import set_echo, set_formatter

from .cli import app
from .console import console, echo, format_text
from .exceptions import CliException


def main():
    # Set CLI mode
    pyinfra.is_cli = True

    # Wire Rich-backed styling/echo into the API output layer
    set_formatter(format_text)
    set_echo(echo)

    # Don't write out deploy.pyc/config.pyc etc
    sys.dont_write_bytecode = True

    sys.path.append(".")

    # Force line buffering
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore

    def _handle_interrupt(signum, frame):
        console.print("Exiting upon user request!")
        sys.exit(0)

    try:
        # Kill any greenlets on ctrl+c
        gevent.signal_handler(signal.SIGINT, gevent.kill)
    except AttributeError:
        # Legacy (gevent <1.2) support
        gevent.signal(signal.SIGINT, gevent.kill)

    signal.signal(signal.SIGINT, _handle_interrupt)  # print the message and exit main

    try:
        app()
    except CliException as e:
        e.show()
        sys.exit(1)
