# pyinfra
# File: pyinfra/modules/server.py
# Desc: server module

from pyinfra.api import command, server


def fact(key):
    return server.fact(key)

@command
def shell(code):
    return code
