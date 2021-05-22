from __future__ import division, print_function, unicode_literals

import re

from functools import wraps
from hashlib import sha1
from inspect import getframeinfo, stack
from os import path, stat
from socket import (
    error as socket_error,
    timeout as timeout_error,
)
from types import GeneratorType

import click
import six

from jinja2 import (
    Environment,
    StrictUndefined,
    TemplateSyntaxError,
    UndefinedError,
)
from paramiko import SSHException

from pyinfra import logger

from .exceptions import PyinfraError

# 64kb chunks
BLOCKSIZE = 65536

# Caches
TEMPLATES = {}
FILE_SHAS = {}

PYINFRA_API_DIR = path.dirname(__file__)


def get_kwargs_str(kwargs):
    if not kwargs:
        return ''

    items = [
        '{0}={1}'.format(key, value)
        for key, value in kwargs.items()
        if key not in ('self', 'state', 'host')
    ]
    return ', '.join(items)


def try_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def memoize(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = '{0}{1}'.format(args, kwargs)
        if key in wrapper.cache:
            return wrapper.cache[key]

        value = func(*args, **kwargs)
        wrapper.cache[key] = value
        return value

    wrapper.cache = {}
    return wrapper


def get_call_location():
    frame = get_caller_frameinfo(frame_offset=1)  # escape *this* function
    return 'line {0} in {1}'.format(
        frame.lineno,
        path.relpath(frame.filename),
    )


def get_caller_frameinfo(frame_offset=0):
    # Default frames to look at is 2; one for this function call itself
    # in util.py and one for the caller of this function within pyinfra
    # giving the external call frame (ie end user deploy code).
    frame_shift = 2 + frame_offset

    stack_items = stack()

    frame = stack_items[frame_shift][0]
    info = getframeinfo(frame)

    del stack_items

    return info


def get_operation_order_from_stack(state):
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
    for stack_item in stack_items[i:]:
        frame = getframeinfo(stack_item[0])

        if frame.filename.startswith(PYINFRA_API_DIR):
            continue

        if state.loop_filename and frame.filename == state.loop_filename:
            line_numbers.extend([state.loop_line, state.loop_counter])

        line_numbers.append(frame.lineno)

    del stack_items

    return line_numbers


def extract_callable_datas(datas):
    for data in datas:
        # Support for dynamic data, ie @deploy wrapped data defaults where
        # the data is stored on the state temporarily.
        if callable(data):
            data = data()

        yield data


class FallbackDict(object):
    '''
    Combines multiple AttrData's to search for attributes.
    '''

    override_datas = None

    def __init__(self, *datas):
        datas = list(datas)

        # Inject an empty override data so we can assign during deploy
        self.__dict__['override_datas'] = {}
        datas.insert(0, self.override_datas)

        self.__dict__['datas'] = tuple(datas)

    def __getattr__(self, key):
        for data in extract_callable_datas(self.datas):
            if key in data:
                return data[key]

    def __setattr__(self, key, value):
        self.override_datas[key] = value

    def __str__(self):
        return six.text_type(self.datas)

    def dict(self):
        out = {}

        # Copy and reverse data objects (such that the first items override
        # the last, matching __getattr__ output).
        datas = list(self.datas)
        datas.reverse()

        for data in extract_callable_datas(datas):
            out.update(data)

        return out


def unroll_generators(generator):
    '''
    Take a generator and unroll any sub-generators recursively. This is
    essentially a Python 2 way of doing `yield from` in Python 3 (given
    iterating the entire thing).
    '''

    # Ensure we have a generator (prevents ccommands returning lists)
    if not isinstance(generator, GeneratorType):
        raise TypeError('{0} is not a generator'.format(generator))

    items = []

    for item in generator:
        if isinstance(item, GeneratorType):
            items.extend(unroll_generators(item))
        else:
            items.append(item)

    return items


def get_template(filename_or_string, is_string=False):
    '''
    Gets a jinja2 ``Template`` object for the input filename or string, with caching
    based on the filename of the template, or the SHA1 of the input string.
    '''

    # Cache against string sha or just the filename
    cache_key = sha1_hash(filename_or_string) if is_string else filename_or_string

    if cache_key in TEMPLATES:
        return TEMPLATES[cache_key]

    if is_string:
        # Set the input string as our template
        template_string = filename_or_string

    else:
        # Load template data into memory
        with open(filename_or_string, 'r') as file_io:
            template_string = file_io.read()

    TEMPLATES[cache_key] = Environment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    ).from_string(template_string)

    return TEMPLATES[cache_key]


def underscore(name):
    '''
    Transform CamelCase -> snake_case.
    '''

    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def sha1_hash(string):
    '''
    Return the SHA1 of the input string.
    '''

    hasher = sha1()
    hasher.update(string.encode('utf-8'))
    return hasher.hexdigest()


def format_exception(e):
    return '{0}{1}'.format(e.__class__.__name__, e.args)


def print_host_combined_output(host, combined_output_lines):
    for type_, line in combined_output_lines:
        if type_ == 'stderr':
            logger.error('{0}{1}'.format(
                host.print_prefix,
                click.style(line, 'red'),
            ))
        else:
            logger.error('{0}{1}'.format(
                host.print_prefix,
                line,
            ))


def log_error_or_warning(host, ignore_errors, description=''):
    log_func = logger.error
    log_color = 'red'
    log_text = 'Error: ' if description else 'Error'

    if ignore_errors:
        log_func = logger.warning
        log_color = 'yellow'
        log_text = 'Error (ignored): ' if description else 'Error (ignored)'

    log_func('{0}{1}{2}'.format(
        host.print_prefix,
        click.style(log_text, log_color),
        description,
    ))


def log_host_command_error(host, e, timeout=0):
    if isinstance(e, timeout_error):
        logger.error('{0}{1}'.format(
            host.print_prefix,
            click.style('Command timed out after {0}s'.format(
                timeout,
            ), 'red'),
        ))

    elif isinstance(e, (socket_error, SSHException)):
        logger.error('{0}{1}'.format(
            host.print_prefix,
            click.style('Command socket/SSH error: {0}'.format(
                format_exception(e)), 'red',
            ),
        ))

    elif isinstance(e, IOError):
        logger.error('{0}{1}'.format(
            host.print_prefix,
            click.style('Command IO error: {0}'.format(
                format_exception(e)), 'red',
            ),
        ))

    # Still here? Re-raise!
    else:
        raise e


@memoize
def show_get_arg_value_warning():
    logger.warning((
        'Use of jinja2 templating in arguments is deprecated, '
        'please use builtin Python string formatting.'
    ))


# TODO: remove this! COMPAT w/<1
def get_arg_value(state, host, arg):
    '''
    This functions is **deprecated**.
    '''

    if isinstance(arg, six.string_types):
        data = {
            'host': host,
            'inventory': state.inventory,
        }

        try:
            rendered_arg = get_template(arg, is_string=True).render(data)
        except (TemplateSyntaxError, UndefinedError) as e:
            raise PyinfraError('Error in template string: {0}'.format(e))
        else:
            if rendered_arg != arg:
                show_get_arg_value_warning()
            return rendered_arg

    elif isinstance(arg, list):
        return [get_arg_value(state, host, value) for value in arg]

    elif isinstance(arg, tuple):
        return tuple(get_arg_value(state, host, value) for value in arg)

    elif isinstance(arg, dict):
        return {
            key: get_arg_value(state, host, value)
            for key, value in six.iteritems(arg)
        }

    return arg


def make_hash(obj):
    '''
    Make a hash from an arbitrary nested dictionary, list, tuple or set, used to generate
    ID's for operations based on their name & arguments.
    '''

    if isinstance(obj, (set, tuple, list)):
        hash_string = ''.join([make_hash(e) for e in obj])

    elif isinstance(obj, dict):
        hash_string = ''.join(
            ''.join((key, make_hash(value)))
            for key, value in six.iteritems(obj)
        )

    else:
        hash_string = (
            # Capture integers first (as 1 == True)
            '{0}'.format(obj) if isinstance(obj, int)
            # Constants - the values can change between hosts but we should still
            # group them under the same operation hash.
            else '_PYINFRA_CONSTANT' if obj in (True, False, None)
            # Plain strings
            else obj if isinstance(obj, six.string_types)
            # Objects with __name__s
            else obj.__name__ if hasattr(obj, '__name__')
            # Objects with names
            else obj.name if hasattr(obj, 'name')
            # Repr anything else
            else repr(obj)
        )

    return sha1_hash(hash_string)


class get_file_io(object):
    '''
    Given either a filename or an existing IO object, this context processor
    will open and close filenames, and leave IO objects alone.
    '''

    close = False

    def __init__(self, filename_or_io, mode='rb'):
        if not (
            # Check we can be read
            hasattr(filename_or_io, 'read')
            # Or we're a filename
            or isinstance(filename_or_io, six.string_types)
        ):
            raise TypeError('Invalid filename or IO object: {0}'.format(
                filename_or_io,
            ))

        self.filename_or_io = filename_or_io
        self.mode = mode

    def __enter__(self):
        # If we have a read attribute, just use the object as-is
        if hasattr(self.filename_or_io, 'read'):
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
        if isinstance(self.filename_or_io, six.string_types):
            return self.filename_or_io


def get_file_sha1(filename_or_io):
    '''
    Calculates the SHA1 of a file or file object using a buffer to handle larger files.
    '''

    file_data = get_file_io(filename_or_io)
    cache_key = file_data.cache_key

    if cache_key and cache_key in FILE_SHAS:
        return FILE_SHAS[cache_key]

    with file_data as file_io:
        hasher = sha1()
        buff = file_io.read(BLOCKSIZE)

        while len(buff) > 0:
            if isinstance(buff, six.text_type):
                buff = buff.encode('utf-8')

            hasher.update(buff)
            buff = file_io.read(BLOCKSIZE)

    digest = hasher.hexdigest()

    if cache_key:
        FILE_SHAS[cache_key] = digest

    return digest


def get_path_permissions_mode(pathname):
    '''
    Get the permissions (bits) of a path as an integer.
    '''

    mode_octal = oct(stat(pathname).st_mode)
    return mode_octal[-3:]
