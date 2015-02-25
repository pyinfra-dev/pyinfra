#!/usr/bin/env python
# pyinfra
# File: docs/build.py
# Desc: boostraps pydocs to auto-generate module documentation

# Monkey patch things first
from gevent.monkey import patch_all
patch_all()

from os import getcwd

# Import host so pyinfra.host exists
from pyinfra.api import host # noqa

from pydocs import build


cwd = getcwd()

# Build module documentation
build(
    cwd,
    'pyinfra.modules',
    'docs/modules',
    index_filename='README'
)

# Build API documentation
build(
    cwd,
    'pyinfra.api',
    'docs/api',
    index_filename='README'
)

print 'Boom, done!'
