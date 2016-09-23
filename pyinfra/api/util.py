# pyinfra
# File: pyinfra/api/util.py
# Desc: utility functions

from __future__ import division, unicode_literals, print_function

import re
from hashlib import sha1
from imp import load_source
from types import GeneratorType

import six
from jinja2 import Template

from .attrs import AttrBase

# 64kb chunks
BLOCKSIZE = 65536

# Template cache
TEMPLATES = {}
FILE_SHAS = {}


def unroll_generators(generator):
    '''
    Take a generator and unroll any sub-generators recursively. This is essentially a
    Python 2 way of doing `yield from` in Python 3 (given iterating the entire thing).
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


def make_command(command, env=None, su_user=None, sudo=False, sudo_user=None):
    '''
    Builds a shell command with various kwargs.
    '''

    # Use env & build our actual command
    if env:
        env_string = ' '.join([
            '{0}={1}'.format(key, value)
            for key, value in six.iteritems(env)
        ])
        command = '{0} {1}'.format(env_string, command)

    # Escape "'s
    command = command.replace("'", "\\'")

    # Switch user with su
    if su_user:
        command = "su {0} -c '{1}'".format(su_user, command)

    # Otherwise just sh wrap the command
    else:
        command = "sh -c '{0}'".format(command)

    # Use sudo (w/user?)
    if sudo:
        if sudo_user:
            command = "sudo -H -u {0} -S {1}".format(sudo_user, command)
        else:
            command = "sudo -H -S {0}".format(command)

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
            'inventory': state.inventory
        }

        return template.render(data)

    elif isinstance(arg, list):
        return [get_arg_value(state, host, value) for value in arg]

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
        if hasattr(self.filename_or_io, 'read'):
            return id(self.filename_or_io)

        else:
            return self.filename_or_io


def get_file_sha1(filename_or_io):
    '''
    Calculates the SHA1 of a file or file object using a buffer to handle larger files.
    '''

    file_data = get_file_io(filename_or_io)

    if file_data.cache_key in FILE_SHAS:
        return FILE_SHAS[file_data.cache_key]

    with file_data as file_io:
        hasher = sha1()
        buff = file_io.read(BLOCKSIZE)

        while len(buff) > 0:
            if isinstance(buff, six.text_type):
                buff = buff.encode('utf-8')

            hasher.update(buff)
            buff = file_io.read(BLOCKSIZE)

    digest = hasher.hexdigest()
    FILE_SHAS[file_data.cache_key] = digest
    return digest


def read_buffer(io, print_output=False, print_func=False):
    '''
    Reads a file-like buffer object into lines and optionally prints the output.
    '''

    def _print(line):
        if print_output:
            if print_func:
                print(print_func(line))
            else:
                print(line)

    out = []

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

    for line in io:
        # Handle local Popen shells returning list of bytes, not strings
        if not isinstance(line, six.text_type):
            line = line.decode('utf-8')

        line = line.strip()
        out.append(line)

        _print(line)

    return out
