#!/usr/bin/env python
# pyinfra
# File: docs/build.py
# Desc: boostraps pydocs to auto-generate module documentation

from os import getcwd

from pydocs import build


cwd = getcwd()

# Build module documentation
build(
    cwd,
    'pyinfra.modules',
    'docs/modules',
    index_filename='README'
)

# Build fact documentation
build(
    cwd,
    'pyinfra.facts',
    'docs/facts',
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
