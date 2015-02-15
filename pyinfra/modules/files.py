# pyinfra
# File: pyinfra/modules/file.py
# Desc: manage files/templates <> server

from pyinfra.api import operation


@operation
def put(local_file, remote_file):
    '''[Not implemented] Copy a local file to the remote system.'''
    pass


@operation
def template(template_name, remote_file, **data):
    '''[Not implemented]Generate a template and write it to the remote system.'''
    pass
