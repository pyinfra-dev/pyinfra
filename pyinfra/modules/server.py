# pyinfra
# File: pyinfra/modules/server.py
# Desc: server module

from pyinfra.api import command, server


def fact(key):
    return server.fact(key)
def all_facts():
    return server.all_facts()
def directory(name):
    return server.directory(name)
def file(name):
    return server.file(name)

@command
def shell(code):
    return code
