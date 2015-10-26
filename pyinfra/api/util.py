# pyinfra
# File: pyinfra/api/util.py
# Desc: utility functions

import re
from copy import deepcopy
from hashlib import sha1

BLOCKSIZE = 65536


def underscore(name):
    '''Transform CamelCase -> snake_case.'''
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def make_hash(obj):
    '''
    Make a hash from an arbitrary nested dictionary, list, tuple or set, used to generate ID's
    for operations based on their name & arguments.
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
