# pyinfra
# File: pyinfra/modules/server.py
# Desc: server module

from pyinfra.api import server, operation


def fact(key):
    return server.fact(key)
def all_facts():
    return server.all_facts()
def directory(name):
    return server.directory(name)
def file(name):
    return server.file(name)


@operation
def shell(code):
    return [code]


@operation
def script(code=None, file=None):
    if code is not None:
        return code

    if file is not None:
        return 'whaaa'
