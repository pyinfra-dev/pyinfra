from __future__ import division, print_function, unicode_literals

import logging

import click
import six

from pyinfra import logger

STDOUT_LOG_LEVELS = (logging.DEBUG, logging.INFO)
STDERR_LOG_LEVELS = (logging.WARNING, logging.ERROR, logging.CRITICAL)


class LogHandler(logging.Handler):
    def __init__(self, use_stderr=False):
        super(LogHandler, self).__init__()
        self._use_stderr = use_stderr

    def emit(self, record):
        try:
            message = self.format(record)
            click.echo(message, err=self._use_stderr)
        except Exception:
            self.handleError(record)


class LogFilter(logging.Filter):
    def __init__(self, *levels):
        self.levels = levels

    def filter(self, record):
        return record.levelno in self.levels


class LogFormatter(logging.Formatter):
    level_to_format = {
        logging.DEBUG: lambda s: click.style(s, 'green'),
        logging.WARNING: lambda s: click.style(s, 'yellow'),
        logging.ERROR: lambda s: click.style(s, 'red'),
        logging.CRITICAL: lambda s: click.style(s, 'red', bold=True),
    }

    def format(self, record):
        message = record.msg

        if record.args:
            message = record.msg % record.args

        # Add path/module info for debug
        if record.levelno is logging.DEBUG:
            path_start = record.pathname.rfind('pyinfra')

            if path_start:
                pyinfra_path = record.pathname[path_start:-3]  # -3 removes `.py`
                module_name = pyinfra_path.replace('/', '.')
                message = '[{0}] {1}'.format(module_name, message)

        # We only handle strings here
        if isinstance(message, six.string_types):
            if '-->' not in message:
                message = '    {0}'.format(message)

            if record.levelno in self.level_to_format:
                message = self.level_to_format[record.levelno](message)

            return message

        # If not a string, pass to standard Formatter
        else:
            return super(LogFormatter, self).format(record)


def setup_logging(log_level):
    # Set the log level
    logger.setLevel(log_level)

    # Setup a new handler for stdout & stderr
    stdout_handler = LogHandler()
    stderr_handler = LogHandler(use_stderr=True)

    # Setup filters to push different levels to different streams
    stdout_filter = LogFilter(*STDOUT_LOG_LEVELS)
    stdout_handler.addFilter(stdout_filter)

    stderr_filter = LogFilter(*STDERR_LOG_LEVELS)
    stderr_handler.addFilter(stderr_filter)

    # Setup a formatter
    formatter = LogFormatter()
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)

    # Add the handlers
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
