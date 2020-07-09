from __future__ import division

import math
import os
import platform
import sys

from collections import deque
from contextlib import contextmanager
from threading import Event, Thread
from time import sleep

import pyinfra

IS_WINDOWS = platform.system() == 'Windows'

WAIT_TIME = 1 / 5
WAIT_CHARS = deque(('-', '/', '|', '\\'))

# Hacky way of getting terminal size (so can clear lines)
# Source: http://stackoverflow.com/questions/566746
IS_TTY = sys.stdout.isatty() and sys.stderr.isatty()
TERMINAL_WIDTH = 0

if IS_TTY:
    try:
        TERMINAL_WIDTH = os.get_terminal_size().columns
    except AttributeError:
        if not IS_WINDOWS:
            terminal_size = os.popen('stty size', 'r').read().split()
            if len(terminal_size) == 2:
                TERMINAL_WIDTH = int(terminal_size[1])


def _print_spinner(stop_event, progress_queue):
    if not IS_TTY or os.environ.get('PYINFRA_PROGRESS') == 'off':
        return

    progress = ''
    text = ''

    while True:
        # Stop when asked too
        if stop_event.is_set():
            break

        WAIT_CHARS.rotate(1)

        try:
            progress = progress_queue[-1]
        except IndexError:
            pass

        text = '    {0}'.format(
            ' '.join((WAIT_CHARS[0], progress)),
        )
        text = '{0}\r'.format(text)

        sys.stderr.write(text)
        sys.stderr.flush()

        # In pyinfra_cli's __main__ we set stdout & stderr to be line buffered,
        # so write this escape code (clear line) into the buffer but don't flush,
        # such that any next print/log/etc clear the line first.
        if not IS_WINDOWS:
            sys.stderr.write('\033[K')

        sleep(WAIT_TIME)


@contextmanager
def progress_spinner(items, prefix_message=None):
    # If there's no pseudo state we're not in CLI mode, so just return a noop
    # handler and exit.
    if not pyinfra.is_cli:
        yield lambda complete_item: None
        return

    if not isinstance(items, set):
        items = set(items)

    total_items = len(items)
    stop_event = Event()

    def make_progress_message(include_items=True):
        message_bits = []

        # If we only have 1 item, don't show %
        if total_items > 1:
            percentage_complete = 0
            complete = total_items - len(items)
            percentage_complete = int(math.floor(complete / total_items * 100))
            message_bits.append('{0}% ({1}/{2})'.format(
                percentage_complete,
                complete,
                total_items,
            ))

        if prefix_message:
            message_bits.append(prefix_message)

        if include_items and items:
            # Plus 3 for the " - " joining below
            message_length = sum((len(message) + 3) for message in message_bits)
            # -8 for padding left+right, -2 for {} wrapping
            items_allowed_width = TERMINAL_WIDTH - 10 - message_length

            if items_allowed_width > 0:
                items_string = '{%s}' % (', '.join('{0}'.format(i) for i in items))
                if len(items_string) >= items_allowed_width:
                    items_string = '%s...}' % (
                        # -3 for the ...
                        items_string[:items_allowed_width - 3],
                    )

                message_bits.append(items_string)

        return ' - '.join(message_bits)

    progress_queue = deque((make_progress_message(),))

    def progress(complete_item):
        if complete_item not in items:
            raise ValueError('Invalid complete item: {0} not in {1}'.format(
                complete_item, items,
            ))

        items.remove(complete_item)
        progress_queue.append(make_progress_message())

    # Kick off the spinner thread
    spinner_thread = Thread(
        target=_print_spinner,
        args=(stop_event, progress_queue),
    )
    spinner_thread.daemon = True
    spinner_thread.start()

    # Yield allowing the actual code the spinner waits for to run
    yield progress

    # Finally, stop the spinner
    stop_event.set()
    spinner_thread.join()
