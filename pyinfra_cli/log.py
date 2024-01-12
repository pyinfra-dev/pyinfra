import logging

import click

from pyinfra import logger, state
from pyinfra.context import ctx_state


class LogHandler(logging.Handler):
    def emit(self, record):
        try:
            message = self.format(record)
            click.echo(message, err=True)
        except Exception:
            self.handleError(record)


class LogFormatter(logging.Formatter):
    previous_was_header = True

    level_to_format = {
        logging.DEBUG: lambda s: click.style(s, "green"),
        logging.WARNING: lambda s: click.style(s, "yellow"),
        logging.ERROR: lambda s: click.style(s, "red"),
        logging.CRITICAL: lambda s: click.style(s, "red", bold=True),
    }

    def format(self, record):
        message = record.msg

        if record.args:
            message = record.msg % record.args

        # Add path/module info for debug
        if record.levelno is logging.DEBUG:
            path_start = record.pathname.rfind("pyinfra")

            if path_start:
                pyinfra_path = record.pathname[path_start:-3]  # -3 removes `.py`
                module_name = pyinfra_path.replace("/", ".")
                message = "[{0}] {1}".format(module_name, message)

        # We only handle strings here
        if isinstance(message, str):
            if ctx_state.isset() and record.levelno is logging.WARNING:
                state.increment_warning_counter()

            if "-->" in message:
                if not self.previous_was_header:
                    click.echo(err=True)
            else:
                message = "    {0}".format(message)

            if record.levelno in self.level_to_format:
                message = self.level_to_format[record.levelno](message)

            self.previous_was_header = "-->" in message
            return message

        # If not a string, pass to standard Formatter
        return super().format(record)


def setup_logging(log_level, other_log_level=None):
    if other_log_level:
        logging.basicConfig(level=other_log_level)

    logger.setLevel(log_level)
    handler = LogHandler()
    formatter = LogFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
