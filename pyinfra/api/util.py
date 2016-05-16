# pyinfra
# File: pyinfra/api/util.py
# Desc: utility functions

from __future__ import division, unicode_literals, print_function

import re
from copy import deepcopy
from hashlib import sha1
from types import FunctionType

import six
from jinja2 import Template

from .attrs import AttrBase

BLOCKSIZE = 65536

# Template cache
TEMPLATES = {}


def import_locals(filename):
    data = {}

    with open(filename) as file:
        exec(file.read(), {}, data)

    return data


def get_template(filename_or_string, is_string=False):
    '''
    Gets a jinja2 ``Template`` object for the input filename or string, with caching
    based on the filename of the template, or the SHA1 of the input string.
    '''

    if is_string:
        # Cache against sha1 of the template
        cache_key = sha1_hash(filename_or_string)

        # Set the input string as our template
        template_string = filename_or_string
    else:
        # Load template data into memory
        file_io = open(filename_or_string)
        template_string = file_io.read()

        # Cache against filename
        cache_key = filename_or_string

    if cache_key in TEMPLATES:
        return TEMPLATES[cache_key]

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


def make_command(command, env=None, sudo=False, sudo_user=None):
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

    # No sudo, just sh wrap the command
    if not sudo:
        command = "sh -c '{0}'".format(command)

    # Otherwise, work out sudo
    else:
        # Sudo with a user, then sh
        if sudo_user:
            command = "sudo -H -u {0} -S sh -c '{1}'".format(sudo_user, command)
        # Sudo then sh
        else:
            command = "sudo -H -S sh -c '{0}'".format(command)

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


def get_arg_name(arg):
    '''
    Returns the name or value of an argument as passed into an operation. Will use pyinfra
    attr key where available, and function names instead of references. See attrs.py for a
    more in-depth description.
    '''

    return (
        arg.pyinfra_attr_key
        if isinstance(arg, AttrBase)
        else arg.__name__
        if isinstance(arg, FunctionType)
        else arg
    )


def make_hash(obj):
    '''
    Make a hash from an arbitrary nested dictionary, list, tuple or set, used to generate
    ID's for operations based on their name & arguments.
    '''

    if type(obj) in (set, tuple, list):
        return hash(tuple([make_hash(e) for e in obj]))

    elif not isinstance(obj, dict):
        return hash(obj)

    new_obj = deepcopy(obj)
    for k, v in new_obj.items():
        new_obj[k] = make_hash(v)

    return hash(tuple(set(new_obj.items())))


def get_file_sha1(filename):
    '''
    Calculates the SHA1 of a file or file object using a buffer to handle larger files.
    '''

    # If we have a read attribute, just use the object as-is
    if hasattr(filename, 'read'):
        file_io = filename

    # Otherwise, assume a filename and open it up
    else:
        file_io = open(filename)

    # Ensure we're at the start of the file
    file_io.seek(0)

    buff = file_io.read(BLOCKSIZE)
    hasher = sha1()

    while len(buff) > 0:
        hasher.update(buff.encode())
        buff = file_io.read(BLOCKSIZE)

    return hasher.hexdigest()


def read_buffer(buff, print_output=False, print_func=False):
    '''
    Reads a file-like buffer object into lines and optionally prints the output.
    '''

    out = []

    for line in buff:
        # Handle local Popen shells returning list of bytes, not strings
        if not isinstance(line, six.text_type):
            line = line.decode('utf-8')

        line = line.strip()
        out.append(line)

        if print_output:
            if print_func:
                print(print_func(line))
            else:
                print(line)

    return out
