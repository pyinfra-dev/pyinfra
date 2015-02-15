#!/usr/bin/env python
# pyinfra
# File: docs/build.py
# Desc: build the docs

# Async things
from gevent import monkey
monkey.patch_all()

from os import path
from glob import glob
from importlib import import_module
from inspect import getmembers, isfunction, getargspec


print '# Auto-building module docs...'
for module_filename in glob('./pyinfra/modules/*.py'):
    module_name = path.basename(module_filename).split('.')[0]
    if module_name == '__init__':
        continue

    print '# Importing module: {}'.format(module_name)
    module = import_module('pyinfra.modules.{}'.format(module_name))
    operations = [
        (name, type)
        for (name, type) in getmembers(module, isfunction)
        if type.__module__ == module.__name__
        and not type.__name__.startswith('_')
    ]

    if not operations:
        continue

    doc_strings = ['# {}'.format(module_name.title())]

    for (name, type) in operations:
        if hasattr(type, 'inline'):
            type = type.inline

        argspec = getargspec(type)
        defaults = dict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults)) if argspec.defaults else {}

        arg_strings = []
        for arg in argspec.args:
            if arg in defaults:
                arg_strings.append('{}={}'.format(arg, defaults[arg]))
            else:
                arg_strings.append(arg)

        doc_strings.append('\n#### {} {}'.format(module_name, name))
        if type.__doc__:
            doc_strings.append('\n{}'.format(type.__doc__))

        doc_strings.append('\n```py\n{}.{}(\n    {}'.format(module_name, name, ',\n    '.join(arg_strings)))
        doc_strings.append(')\n```')

    doc_strings = [str(s) for s in doc_strings]
    doc_strings.append('')

    print '# Writing file: modules/{}.md'.format(module_name)
    doc_file = open('./docs/modules/{}.md'.format(module_name), 'w')
    doc_file.write('\n'.join(doc_strings))
    doc_file.close()

print '# Done!'
