from functools import wraps
from hashlib import sha1
from inspect import getframeinfo, getfullargspec, stack
from os import getcwd, path, stat
from socket import error as socket_error, timeout as timeout_error
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import click
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from paramiko import SSHException

import pyinfra
from pyinfra import logger

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State

# 64kb chunks
BLOCKSIZE = 65536

# Caches
TEMPLATES: Dict[Any, Any] = {}
FILE_SHAS: Dict[Any, Any] = {}

PYINFRA_API_DIR = path.dirname(__file__)


def get_file_path(state: "State", filename: str):
    if path.isabs(filename):
        return filename

    assert state.cwd is not None, "Cannot use `get_file_path` with no `state.cwd` set"
    relative_to = state.cwd

    if state.current_exec_filename and (filename.startswith("./") or filename.startswith(".\\")):
        relative_to = path.dirname(state.current_exec_filename)

    return path.join(relative_to, filename)


def get_args_kwargs_spec(func: Callable[..., Any]) -> Tuple[List, Dict]:
    args: List[Any] = []
    kwargs: Dict[Any, Any] = {}

    argspec = getfullargspec(func)
    if not argspec.args:
        return args, kwargs

    if argspec.defaults:
        kwargs = dict(
            zip(
                argspec.args[-len(argspec.defaults) :],
                argspec.defaults,
            ),
        )
        args = argspec.args[: -len(argspec.defaults)]
    else:
        args = argspec.args

    return args, kwargs


def get_kwargs_str(kwargs: Dict[Any, Any]):
    if not kwargs:
        return ""

    items = [
        "{0}={1}".format(key, value)
        for key, value in sorted(kwargs.items())
        if key not in ("self", "state", "host")
    ]
    return ", ".join(items)


def try_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def memoize(func: Callable[..., Any]):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = "{0}{1}".format(args, kwargs)
        if key in wrapper.cache:
            return wrapper.cache[key]

        value = func(*args, **kwargs)
        wrapper.cache[key] = value
        return value

    wrapper.cache = {}  # type: ignore
    return wrapper


def get_call_location(frame_offset: int = 1):
    frame = get_caller_frameinfo(frame_offset=frame_offset)  # escape *this* function
    relpath = frame.filename

    try:
        # On Windows if pyinfra is on a different drive to the filename here, this will
        # error as there's no way to do relative paths between drives.
        relpath = path.relpath(frame.filename)
    except ValueError:
        pass

    return "line {0} in {1}".format(frame.lineno, relpath)


def get_caller_frameinfo(frame_offset: int = 0):
    # Default frames to look at is 2; one for this function call itself
    # in util.py and one for the caller of this function within pyinfra
    # giving the external call frame (ie end user deploy code).
    frame_shift = 2 + frame_offset

    stack_items = stack()

    frame = stack_items[frame_shift][0]
    info = getframeinfo(frame)

    del stack_items

    return info


def get_operation_order_from_stack(state: "State"):
    stack_items = list(reversed(stack()))

    # Find the *first* occurrence of our deploy file in the reversed stack
    if state.current_deploy_filename:
        for i, stack_item in enumerate(stack_items):
            frame = getframeinfo(stack_item[0])
            if frame.filename == state.current_deploy_filename:
                break
    else:
        i = 0

    # Now generate a list of line numbers *following that file*
    line_numbers = []

    if pyinfra.is_cli:
        line_numbers.append(state.current_op_file_number)

    for stack_item in stack_items[i:]:
        frame = getframeinfo(stack_item[0])

        if frame.filename.startswith(PYINFRA_API_DIR):
            continue

        line_numbers.append(frame.lineno)

    del stack_items

    return line_numbers


def get_template(filename_or_io: str):
    """
    Gets a jinja2 ``Template`` object for the input filename or string, with caching
    based on the filename of the template, or the SHA1 of the input string.
    """

    file_data = get_file_io(filename_or_io, mode="r")
    cache_key = file_data.cache_key

    if cache_key and cache_key in TEMPLATES:
        return TEMPLATES[cache_key]

    with file_data as file_io:
        template_string = file_io.read()

    template = Environment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        loader=FileSystemLoader(getcwd()),
    ).from_string(template_string)

    if cache_key:
        TEMPLATES[cache_key] = template

    return template


def sha1_hash(string: str):
    """
    Return the SHA1 of the input string.
    """

    hasher = sha1()
    hasher.update(string.encode("utf-8"))
    return hasher.hexdigest()


def format_exception(e):
    return "{0}{1}".format(e.__class__.__name__, e.args)


def print_host_combined_output(host: "Host", combined_output_lines):
    for type_, line in combined_output_lines:
        if type_ == "stderr":
            logger.error(
                "{0}{1}".format(
                    host.print_prefix,
                    click.style(line, "red"),
                ),
            )
        else:
            logger.error(
                "{0}{1}".format(
                    host.print_prefix,
                    line,
                ),
            )


def log_operation_start(op_meta: Dict, op_types: Optional[List] = None, prefix: str = "--> "):
    op_types = op_types or []
    if op_meta["serial"]:
        op_types.append("serial")
    if op_meta["run_once"]:
        op_types.append("run once")

    args = ""
    if op_meta["args"]:
        args = "({0})".format(", ".join(str(arg) for arg in op_meta["args"]))

    logger.info(
        "{0} {1} {2}".format(
            click.style(
                "{0}Starting{1}operation:".format(
                    prefix,
                    " {0} ".format(", ".join(op_types)) if op_types else " ",
                ),
                "blue",
            ),
            click.style(", ".join(op_meta["names"]), bold=True),
            args,
        ),
    )


def log_error_or_warning(
    host: "Host", ignore_errors: bool, description: str = "", continue_on_error: bool = False
):
    log_func = logger.error
    log_color = "red"
    log_text = "Error: " if description else "Error"

    if ignore_errors:
        log_func = logger.warning
        log_color = "yellow"
        log_text = (
            "Error (ignored, execution continued)" if continue_on_error else "Error (ignored)"
        )
        if description:
            log_text = f"{log_text}: "

    log_func(
        "{0}{1}{2}".format(
            host.print_prefix,
            click.style(log_text, log_color),
            description,
        ),
    )


def log_host_command_error(host: "Host", e, timeout: int = 0):
    if isinstance(e, timeout_error):
        logger.error(
            "{0}{1}".format(
                host.print_prefix,
                click.style(
                    "Command timed out after {0}s".format(
                        timeout,
                    ),
                    "red",
                ),
            ),
        )

    elif isinstance(e, (socket_error, SSHException)):
        logger.error(
            "{0}{1}".format(
                host.print_prefix,
                click.style(
                    "Command socket/SSH error: {0}".format(format_exception(e)),
                    "red",
                ),
            ),
        )

    elif isinstance(e, IOError):
        logger.error(
            "{0}{1}".format(
                host.print_prefix,
                click.style(
                    "Command IO error: {0}".format(format_exception(e)),
                    "red",
                ),
            ),
        )

    # Still here? Re-raise!
    else:
        raise e


def make_hash(obj):
    """
    Make a hash from an arbitrary nested dictionary, list, tuple or set, used to generate
    ID's for operations based on their name & arguments.
    """

    if isinstance(obj, (set, tuple, list)):
        hash_string = "".join([make_hash(e) for e in obj])

    elif isinstance(obj, dict):
        hash_string = "".join("".join((key, make_hash(value))) for key, value in obj.items())

    else:
        hash_string = (
            # Capture integers first (as 1 == True)
            "{0}".format(obj)
            if isinstance(obj, int)
            # Constants - the values can change between hosts but we should still
            # group them under the same operation hash.
            else "_PYINFRA_CONSTANT"
            if obj in (True, False, None)
            # Plain strings
            else obj
            if isinstance(obj, str)
            # Objects with __name__s
            else obj.__name__
            if hasattr(obj, "__name__")
            # Objects with names
            else obj.name
            if hasattr(obj, "name")
            # Repr anything else
            else repr(obj)
        )

    return sha1_hash(hash_string)


class get_file_io:
    """
    Given either a filename or an existing IO object, this context processor
    will open and close filenames, and leave IO objects alone.
    """

    close = False

    def __init__(self, filename_or_io, mode="rb"):
        if not (
            # Check we can be read
            hasattr(filename_or_io, "read")
            # Or we're a filename
            or isinstance(filename_or_io, str)
        ):
            raise TypeError(
                "Invalid filename or IO object: {0}".format(
                    filename_or_io,
                ),
            )

        self.filename_or_io = filename_or_io
        self.mode = mode

    def __enter__(self):
        # If we have a read attribute, just use the object as-is
        if hasattr(self.filename_or_io, "read"):
            file_io = self.filename_or_io

        # Otherwise, assume a filename and open it up
        else:
            file_io = open(self.filename_or_io, self.mode)

            # Attach to self for closing on __exit__
            self.file_io = file_io
            self.close = True

        # Ensure we're at the start of the file
        file_io.seek(0)
        return file_io

    def __exit__(self, type, value, traceback):
        if self.close:
            self.file_io.close()

    @property
    def cache_key(self):
        # If we're a filename, cache against that - we don't cache in-memory
        # file objects.
        if isinstance(self.filename_or_io, str):
            return self.filename_or_io


def get_file_sha1(filename_or_io):
    """
    Calculates the SHA1 of a file or file object using a buffer to handle larger files.
    """

    file_data = get_file_io(filename_or_io)
    cache_key = file_data.cache_key

    if cache_key and cache_key in FILE_SHAS:
        return FILE_SHAS[cache_key]

    with file_data as file_io:
        hasher = sha1()
        buff = file_io.read(BLOCKSIZE)

        while len(buff) > 0:
            if isinstance(buff, str):
                buff = buff.encode("utf-8")

            hasher.update(buff)
            buff = file_io.read(BLOCKSIZE)

    digest = hasher.hexdigest()

    if cache_key:
        FILE_SHAS[cache_key] = digest

    return digest


def get_path_permissions_mode(pathname: str):
    """
    Get the permissions (bits) of a path as an integer.
    """

    mode_octal = oct(stat(pathname).st_mode)
    return mode_octal[-3:]
