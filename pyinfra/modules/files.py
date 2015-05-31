# pyinfra
# File: pyinfra/modules/file.py
# Desc: manage files/templates <> server

from cStringIO import StringIO

from jinja2 import Template

from pyinfra.api import operation


@operation
def put(local_file, remote_file):
    '''Copy a local file to the remote system.'''
    # Just load the local file
    local_file = open(local_file, 'r')

    return [(local_file, remote_file)]


@operation
def template(template_file, remote_file, **data):
    '''Generate a template and write it to the remote system.'''
    # Load the template from file
    template_file = open(template_file, 'r')
    template = Template(template_file.read())

    # Render and make file-like it's output
    output = template.render(data)
    output_file = StringIO(output)

    return [(output_file, remote_file)]
