# pyinfra
# File: pyinfra/api/util.py
# Desc: utility functions

import re
from copy import deepcopy
from hashlib import sha1
from types import FunctionType

from .attrs import AttrBase

BLOCKSIZE = 65536


def underscore(name):
    '''Transform CamelCase -> snake_case.'''

    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def sha1_hash(string):
    '''Return the SHA1 of the input string.'''

    hasher = sha1()
    hasher.update(string)
    return hasher.hexdigest()


def make_command(command, env=None, sudo=False, sudo_user=None):
    # Use env & build our actual command
    if env:
        env_string = ' '.join([
            '{0}={1}'.format(key, value)
            for key, value in env.iteritems()
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


def get_file_sha1(io):
    '''Calculates the SHA1 of a file object using a buffer to handle larger files.'''

    buff = io.read(BLOCKSIZE)
    hasher = sha1()

    while len(buff) > 0:
        hasher.update(buff)
        buff = io.read(BLOCKSIZE)

    # Reset the IO read
    io.seek(0)
    return hasher.hexdigest()


def read_buffer(buff, print_output=False, print_func=False):
    '''Reads a file-like buffer object into lines and optionally prints the output.'''

    out = []

    for line in buff:
        line = line.strip()
        out.append(line)

        if print_output:
            if print_func:
                print print_func(line)
            else:
                print line

    return out
