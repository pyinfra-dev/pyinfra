from __future__ import division, print_function, unicode_literals

import re

from functools import wraps
from hashlib import sha1
from inspect import getframeinfo, stack
from socket import (
    error as socket_error,
    timeout as timeout_error,
)
from types import GeneratorType

import click
import six

from jinja2 import Template, TemplateSyntaxError, UndefinedError
from paramiko import SSHException
from six.moves import shlex_quote

from pyinfra import logger
from pyinfra.api import Config

from .exceptions import PyinfraError
from .operation_kwargs import OPERATION_KWARGS

# 64kb chunks
BLOCKSIZE = 65536

# Caches
TEMPLATES = {}
FILE_SHAS = {}


def try_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def ensure_host_list(hosts, inventory):
    if hosts is None:
        return hosts

    # If passed a string, treat as group name and get any hosts from inventory
    if isinstance(hosts, six.string_types):
        return inventory.get_group(hosts, [])

    if not isinstance(hosts, (list, tuple)):
        return [hosts]

    return hosts


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


@memoize
def show_stdin_global_warning():
    logger.warning('The stdin global argument is in alpha!')


def pop_global_op_kwargs(state, kwargs):
    '''
    Pop and return operation global keyword arguments.
    '''

    for deprecated_key in ('when', 'hosts'):
        if deprecated_key in kwargs:
            logger.warning((
                'Use of the `{0}` argument is deprecated, '
                'please use normal `if` statements instead.'
            ).format(deprecated_key))

    meta_kwargs = state.deploy_kwargs or {}

    def get_kwarg(key, default=None):
        return kwargs.pop(key, meta_kwargs.get(key, default))

    # TODO: remove hosts/when
    hosts = get_kwarg('hosts')
    hosts = ensure_host_list(hosts, inventory=state.inventory)

    # Filter out any hosts not in the meta kwargs (nested support)
    if meta_kwargs.get('hosts') is not None:
        hosts = [
            host for host in hosts
            if host in meta_kwargs['hosts']
        ]

    global_kwargs = {
        'hosts': hosts,
        'when': get_kwarg('when', True),
    }
    # TODO: end remove hosts/when block

    if 'stdin' in kwargs:
        show_stdin_global_warning()

    for _, kwarg_configs in OPERATION_KWARGS.items():
        for key, config in kwarg_configs.items():
            handler = None
            default = None

            if isinstance(config, dict):
                handler = config.get('handler')
                default = config.get('default')
                if default and callable(default):
                    default = default(state.config)

            value = get_kwarg(key, default=default)
            if handler:
                value = handler(state.config, value)

            global_kwargs[key] = value

    return global_kwargs


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

    TEMPLATES[cache_key] = Template(template_string, keep_trailing_newline=True)
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
    hasher.update(string.encode())
    return hasher.hexdigest()


def format_exception(e):
    return '{0}{1}'.format(e.__class__.__name__, e.args)


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


def make_command(
    command,
    env=None,
    su_user=Config.SU_USER,
    use_su_login=Config.USE_SU_LOGIN,
    sudo=Config.SUDO,
    sudo_user=Config.SUDO_USER,
    use_sudo_login=Config.USE_SUDO_LOGIN,
    preserve_sudo_env=Config.PRESERVE_SUDO_ENV,
    shell_executable=Config.SHELL,
):
    '''
    Builds a shell command with various kwargs.
    '''

    debug_meta = {}

    for key, value in (
        ('shell_executable', shell_executable),
        ('sudo', sudo),
        ('sudo_user', sudo_user),
        ('su_user', su_user),
        ('env', env),
    ):
        if value:
            debug_meta[key] = value

    logger.debug('Building command ({0}): {1}'.format(' '.join(
        '{0}: {1}'.format(key, value)
        for key, value in six.iteritems(debug_meta)
    ), command))

    # Use env & build our actual command
    if env:
        env_string = ' '.join([
            '{0}={1}'.format(key, value)
            for key, value in six.iteritems(env)
        ])
        command = 'export {0}; {1}'.format(env_string, command)

    # Quote the command as a string
    command = shlex_quote(command)

    # Switch user with su
    if su_user:
        su_bits = ['su']

        if use_su_login:
            su_bits.append('-l')

        # note `which <shell>` usage here - su requires an absolute path
        command = '{0} {1} -s `which {2}` -c {3}'.format(
            ' '.join(su_bits), su_user, shell_executable, command,
        )

    # Otherwise just sh wrap the command
    else:
        command = '{0} -c {1}'.format(shell_executable, command)

    # Use sudo (w/user?)
    if sudo:
        sudo_bits = ['sudo', '-S', '-H', '-n']

        if use_sudo_login:
            sudo_bits.append('-i')

        if preserve_sudo_env:
            sudo_bits.append('-E')

        if sudo_user:
            sudo_bits.extend(('-u', sudo_user))

        command = '{0} {1}'.format(' '.join(sudo_bits), command)

    return command


def get_arg_value(state, host, arg):
    '''
    Runs string arguments through the jinja2 templating system with a state and
    host. Used to avoid string formatting in deploy operations which result in
    one operation per host/variable. By parsing the commands after we generate
    the ``op_hash``, multiple command variations can fall under one op.
    '''

    if isinstance(arg, six.string_types):
        data = {
            'host': host,
            'inventory': state.inventory,
        }

        try:
            return get_template(arg, is_string=True).render(data)
        except (TemplateSyntaxError, UndefinedError) as e:
            raise PyinfraError('Error in template string: {0}'.format(e))

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
            # Constants - the values can change between hosts but we should still
            # group them under the same operation hash.
            '_PYINFRA_CONSTANT' if obj in (True, False, None)
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


def read_buffer(type_, io, output_queue, print_output=False, print_func=None):
    '''
    Reads a file-like buffer object into lines and optionally prints the output.
    '''

    def _print(line):
        if print_func:
            line = print_func(line)

        if six.PY2:  # Python2 must print unicode as bytes (encoded)
            line = line.encode('utf-8')

        click.echo(line)

    for line in io:
        # Handle local Popen shells returning list of bytes, not strings
        if not isinstance(line, six.text_type):
            line = line.decode('utf-8')

        line = line.strip()
        output_queue.put((type_, line))

        if print_output:
            _print(line)
