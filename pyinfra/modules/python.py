# pyinfra
# File: pyinfra/modules/python.py
# Desc: module to enable execution Python code mid-deploy

'''
The Python module allows you to execute Python code within the context of a deploy.
'''

from pyinfra.api import operation


@operation
def execute(state, host, callback, *args, **kwargs):
    return [(callback, args, kwargs)]
