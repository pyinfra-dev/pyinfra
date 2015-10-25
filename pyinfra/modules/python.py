# pyinfra
# File: pyinfra/modules/python.py
# Desc: module to enable execution Python code mid-deploy

from pyinfra.api import operation

'''
The Python module allows you to execute Python code within the context of a deploy.
'''

@operation
def execute(state, host, callback, *args, **kwargs):
    return [(callback, args, kwargs)]
