# pyinfra
# File: pyinfra/cli/log.py
# Desc: logging for the CLI

import logging
import re
import sys

import six

from termcolor import colored

from pyinfra import logger

STDOUT_LOG_LEVELS = (logging.DEBUG, logging.INFO)
STDERR_LOG_LEVELS = (logging.WARNING, logging.ERROR, logging.CRITICAL)


class LogFilter(logging.Filter):
    def __init__(self, *levels):
        self.levels = levels

    def filter(self, record):
        return record.levelno in self.levels


class LogFormatter(logging.Formatter):
    level_to_format = {
        logging.DEBUG: lambda s: colored(s, 'green'),
        logging.WARNING: lambda s: colored(s, 'yellow'),
        logging.ERROR: lambda s: colored(s, 'red'),
        logging.CRITICAL: lambda s: colored(s, 'red', attrs=['bold']),
    }

    def format(self, record):
        message = record.msg

        # We only handle strings here
        if isinstance(message, six.string_types):
            # Horrible string matching hack
            if re.match(r'.*Starting[ a-zA-Z,]*operation.*', message):
                message = '--> {0}'.format(message)
            else:
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
    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)

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
