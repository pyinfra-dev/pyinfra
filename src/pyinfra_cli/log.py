import logging

from rich.text import Text
from typing_extensions import override

from pyinfra import logger, state
from pyinfra.context import ctx_state

from . import routing
from .console import console, format_text


class LogHandler(logging.Handler):
    @override
    def emit(self, record):
        try:
            # Count warnings here (not in the formatter) so the counter also
            # works when messages are routed into the live tree.
            if ctx_state.isset() and record.levelno == logging.WARNING:
                state.increment_warning_counter()

            message = record.getMessage()
            host_name, text = routing.attribute_host(message)

            # Record per-host warnings/errors so failure prompts can show
            # which hosts failed and why, in every output mode.
            if host_name is not None and record.levelno >= logging.WARNING:
                routing.record_host_error(host_name, text)

            tree = routing.get_tree()
            if tree is not None:
                if host_name is not None and tree.is_active:
                    # Host warnings/errors always nest under the host's tree
                    # node; INFO lines (Connected/Ready/Loaded fact/...) only
                    # in verbose mode — at default verbosity the node status
                    # already conveys them.
                    if record.levelno >= logging.WARNING or tree.verbose:
                        tree.add_host_detail(
                            host_name, text, is_error=record.levelno >= logging.ERROR
                        )
                    return
                if host_name is None and record.levelno < logging.WARNING:
                    # Non-host INFO lines (phase headers) are dropped: the tree
                    # already conveys the phases.
                    return
                # Everything else streams to the console: non-host warnings/
                # errors (above the live region) and host lines emitted while
                # no live region is running (e.g. disconnect notices).

            console.print(Text.from_ansi(self.format(record)))
        except Exception:
            self.handleError(record)


class LogFormatter(logging.Formatter):
    previous_was_header = True

    level_to_format = {
        logging.DEBUG: lambda s: format_text(s, "green"),
        logging.WARNING: lambda s: format_text(s, "yellow"),
        logging.ERROR: lambda s: format_text(s, "red"),
        logging.CRITICAL: lambda s: format_text(s, "red", bold=True),
    }

    @override
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
                message = f"[{module_name}] {message}"

        # We only handle strings here
        if isinstance(message, str):
            # Header lines are top-level phase messages; per-host lines start
            # with the host's print prefix and are indented beneath their
            # header. Match on the ANSI-stripped prefix (host names may be
            # styled).
            prefix_host, _ = routing.split_host_prefix(routing.strip_ansi(message))
            is_header = prefix_host is None

            if is_header:
                if not self.previous_was_header:
                    console.print()
            else:
                message = f"    {message}"

            if record.levelno in self.level_to_format:
                message = self.level_to_format[record.levelno](message)

            self.previous_was_header = is_header
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
