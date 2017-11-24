# pyinfra
# File: pyinfra/api/util.py
# Desc: utility functions

from __future__ import division, print_function, unicode_literals

import re
from hashlib import sha1
from imp import load_source
from socket import (
    error as socket_error,
    timeout as timeout_error,
)
from types import GeneratorType

import click
import six

from jinja2 import Template
from paramiko import SSHException
from six.moves import shlex_quote

from pyinfra import logger

from .attrs import AttrBase

# 64kb chunks
BLOCKSIZE = 65536

# Template cache
TEMPLATES = {}
FILE_SHAS = {}


def ensure_host_list(hosts, inventory):
    if hosts is None:
        return hosts

    # If passed a string, treat as group name and get hosts from inventory
    if isinstance(hosts, six.string_types):
        return inventory.get_group(hosts)

    if not isinstance(hosts, (list, tuple)):
        return [hosts]

    return hosts


def pop_op_kwargs(state, kwargs):
    '''
    Pop and return operation global keyword arguments.
    '''

    meta_kwargs = state.deploy_kwargs or {}

    def get_kwarg(key, default=None):
        return kwargs.pop(key, meta_kwargs.get(key, default))

    # Get the env for this host: config env followed by command-level env
    env = state.config.ENV.copy()
    env.update(get_kwarg('env', {}))

    hosts = get_kwarg('hosts')
    hosts = ensure_host_list(hosts, inventory=state.inventory)

    # Filter out any hosts not in the meta kwargs (nested support)
    if meta_kwargs.get('hosts') is not None:
        hosts = [
            host for host in hosts
            if host in meta_kwargs['hosts']
        ]

    return {
        # ENVars for commands in this operation
        'env': env,
        # Hosts to limit the op to
        'hosts': hosts,
        # When to limit the op (default always)
        'when': get_kwarg('when', True),
        # Locally & globally configurable
        'sudo': get_kwarg('sudo', state.config.SUDO),
        'sudo_user': get_kwarg('sudo_user', state.config.SUDO_USER),
        'su_user': get_kwarg('su_user', state.config.SU_USER),
        # Whether to preserve ENVars when sudoing (eg SSH forward agent socket)
        'preserve_sudo_env': get_kwarg(
            'preserve_sudo_env', state.config.PRESERVE_SUDO_ENV,
        ),
        # Ignore any errors during this operation
        'ignore_errors': get_kwarg(
            'ignore_errors', state.config.IGNORE_ERRORS,
        ),
        # Timeout on running the command
        'timeout': get_kwarg('timeout'),
        # Get a PTY before executing commands
        'get_pty': get_kwarg('get_pty', False),
        # Forces serial mode for this operation (--serial for one op)
        'serial': get_kwarg('serial', False),
        # Only runs this operation once
        'run_once': get_kwarg('run_once', False),
        # Execute in batches of X hosts rather than all at once
        'parallel': get_kwarg('parallel'),
        # Callbacks
        'on_success': get_kwarg('on_success'),
        'on_error': get_kwarg('on_error'),
        # Operation hash
        'op': get_kwarg('op'),
    }


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


def exec_file(filename, return_locals=False):
    '''
    Execute a Python file and optionally return it's attributes as a dict.
    '''

    module_name = '_pyinfra_{0}'.format(filename.replace('.', '_'))
    module = load_source(module_name, filename)

    if return_locals:
        return {
            key: getattr(module, key)
            for key in dir(module)
        }


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


def make_command(
    command,
    env=None,
    su_user=None,
    sudo=False,
    sudo_user=None,
    preserve_sudo_env=False,
):
    '''
    Builds a shell command with various kwargs.
    '''

    debug_meta = {}

    for key, value in (
        ('sudo', sudo),
        ('sudo_user', sudo_user),
        ('su_user', su_user),
        ('env', env),
    ):
        if value:
            debug_meta[key] = value

    logger.debug('Building command ({0})'.format(' '.join(
        '{0}: {1}'.format(key, value)
        for key, value in six.iteritems(debug_meta)
    )))

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
        command = 'su {0} -c {1}'.format(su_user, command)

    # Otherwise just sh wrap the command
    else:
        command = 'sh -c {0}'.format(command)

    # Use sudo (w/user?)
    if sudo:
        sudo_bits = ['sudo', '-H']

        if preserve_sudo_env:
            sudo_bits.append('-E')

        if sudo_user:
            sudo_bits.extend(('-u', sudo_user))

        command = '{0} {1}'.format(' '.join(sudo_bits), command)

    return command


def get_arg_value(state, host, arg):
    '''
    Runs string arguments through the jinja2 templating system with a state and host. Used
    to avoid string formatting in deploy operations which result in one operation per
    host/variable. By parsing the commands after we generate the ``op_hash``, multiple
    command variations can fall under one op.
    '''

    if isinstance(arg, six.string_types):
        template = get_template(arg, is_string=True)
        data = {
            'host': host,
            'inventory': state.inventory,
        }

        return template.render(data)

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
            # pyinfra attr key where available (host/inventory data), see attrs.py
            obj.pyinfra_attr_key if isinstance(obj, AttrBase)
            # Plain strings
            else obj if isinstance(obj, six.string_types)
            # Objects with names
            else obj.__name__ if hasattr(obj, '__name__')
            # Repr anything else
            else repr(obj)
        )

    return sha1_hash(hash_string)


class get_file_io(object):
    '''
    Given either a filename or an existing IO object, this context processor will open
    and close filenames, and leave IO objects alone.
    '''

    close = False

    def __init__(self, filename_or_io):
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

    def __enter__(self):
        # If we have a read attribute, just use the object as-is
        if hasattr(self.filename_or_io, 'read'):
            file_io = self.filename_or_io

        # Otherwise, assume a filename and open it up
        else:
            file_io = open(self.filename_or_io, 'rb')

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


def read_buffer(io, print_output=False, print_func=False):
    '''
    Reads a file-like buffer object into lines and optionally prints the output.
    '''

    # TODO: research this further - some steps towards handling stdin (ie password requests
    # from programs that don't notice there's no TTY to accept passwords from!). This just
    # prints output as below, but stores partial lines in a buffer, which could be printed
    # when ready to accept input. Or detected and raise an error.

    # GitHub issue: https://github.com/Fizzadar/pyinfra/issues/40

    # buff = ''
    # data = io.read(1)

    # while data:
    #     # Append to the buffer
    #     buff += data

    #     # Newlines in the buffer? Break them out
    #     if '\n' in buff:
    #         lines = buff.split('\n')

    #         # Set the buffer back to just the last line
    #         buff = lines[-1]

    #         # Get the other lines, strip them
    #         lines = [
    #             line.strip()
    #             for line in lines[:-1]
    #         ]

    #         out.extend(lines)

    #         for line in lines:
    #             _print(line)

    #     # Get next data
    #     data = io.read(1)

    # if buff:
    #     line = buff.strip()
    #     out.append(line)
    #     _print(line)

    def _print(line):
        if print_output:
            if print_func:
                print(print_func(line))
            else:
                print(line)

    out = []

    for line in io:
        # Handle local Popen shells returning list of bytes, not strings
        if not isinstance(line, six.text_type):
            line = line.decode('utf-8')

        line = line.strip()
        out.append(line)

        _print(line)

    return out
