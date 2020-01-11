#!/usr/bin/env python

import re
from importlib import import_module
from inspect import getargspec, getmembers
from os import path
from types import FunctionType

import six

from six.moves import range

from pyinfra import modules

MODULE_DEF_LINE_MAX = 90


def _title_line(char, string):
    return ''.join(char for _ in range(0, len(string)))


def _format_doc_line(line):
    # Bold the <arg>: part of each line
    line = re.sub(r'\+ ([a-z_\/]+)(.*)', r'+ **\1**\2', line)

    # Strip the first 4 characters (first indent from docstring)
    return line[4:]


def build_facts():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, '..', 'docs'))

    for module_name in modules.__all__:
        lines = []

        print('--> Doing module: {0}'.format(module_name))
        module = import_module('pyinfra.modules.{0}'.format(module_name))

        lines.append(module_name.title())
        lines.append(_title_line('-', module_name))
        lines.append('')

        if module.__doc__:
            lines.append(module.__doc__)

        operation_functions = [
            (key, value._pyinfra_op)
            for key, value in getmembers(module)
            if (
                isinstance(value, FunctionType)
                and value.__module__ == module.__name__
                and getattr(value, '_pyinfra_op', False)
                and not value.__name__.startswith('_')
                and not key.startswith('_')
            )
        ]

        for name, func in operation_functions:
            title_name = ':code:`{0}.{1}`'.format(module_name, name)
            lines.append(title_name)

            # Underline name with -'s for title
            lines.append(_title_line('~', title_name))

            doc = func.__doc__
            if doc:
                docbits = doc.strip().split('\n')
                description_lines = []

                for line in docbits:
                    if line:
                        description_lines.append(line)
                    else:
                        break

                if len(docbits) > 0:
                    lines.append('')
                    lines.extend([line.strip() for line in description_lines])
                    lines.append('')
                    doc = '\n'.join(docbits[len(description_lines):])

            argspec = getargspec(func)

            # Make default strings appear as strings
            arg_defaults = [
                "'{}'".format(arg) if isinstance(arg, six.string_types) else arg
                for arg in argspec.defaults
            ] if argspec.defaults else None

            # Create a dict of arg name -> default
            defaults = dict(zip(
                argspec.args[-len(arg_defaults):],
                arg_defaults,
            )) if arg_defaults else {}

            # Build args string
            args = [
                '{0}={1}'.format(arg, defaults[arg])
                if arg in defaults else arg
                for arg in argspec.args[2:]
            ]

            if len(', '.join(args)) <= MODULE_DEF_LINE_MAX:
                args_string = ', '.join(args)

            else:
                arg_buffer = []
                arg_lines = []
                for arg in args:
                    if len(', '.join(arg_buffer + [arg])) >= MODULE_DEF_LINE_MAX:
                        arg_lines.append(arg_buffer)
                        arg_buffer = []

                    arg_buffer.append(arg)

                if arg_buffer:
                    arg_lines.append(arg_buffer)

                arg_lines = [
                    '        {0}'.format(', '.join(line_args))
                    for line_args in arg_lines
                ]

                args_string = '\n{0}\n    '.format(',\n'.join(arg_lines))

            # Attach the code block
            lines.append('''
.. code:: python

    {0}.{1}({2})

'''.strip().format(module_name, name, args_string))

            # Append any remaining docstring
            if doc:
                lines.append('')
                lines.append('{0}'.format('\n'.join([
                    _format_doc_line(line) for line in doc.split('\n')
                ])).strip())

            lines.append('')
            lines.append('')

        # Write out the file
        module_filename = path.join(docs_dir, 'modules', '{0}.rst'.format(module_name))
        print('--> Writing {0}'.format(module_filename))

        out = '\n'.join(lines)

        outfile = open(module_filename, 'w')
        outfile.write(out)
        outfile.close()


if __name__ == '__main__':
    print('### Building module docs')
    build_facts()
