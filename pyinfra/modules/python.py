# pyinfra
# File: pyinfra/modules/python.py
# Desc: module to enable execution Python code mid-deploy

from pyinfra.api import operation


@operation
def execute(callback, **kwargs):
    return [(callback, kwargs)]
