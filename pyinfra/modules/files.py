# pyinfra
# File: pyinfra/modules/file.py
# Desc: manage files/templates <> server

from pyinfra.api import operation


@operation
def put(local_file, remote_file):
    pass


@operation
def template(template_name, remote_file, **data):
    pass
