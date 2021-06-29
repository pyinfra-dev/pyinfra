#!/usr/bin/env python

from inspect import getargspec, getmembers, isclass
from os import path
from types import FunctionType, MethodType

import six

from six.moves import range

from pyinfra import facts
from pyinfra.api.facts import FactBase, ShortFactBase


def _title_line(char, string):
    return ''.join(char for _ in range(0, len(string)))


def build_facts():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, '..', 'docs'))

    # Now we generate a facts.rst describing the use of the facts as:
    # host.data.<snake_case_fact>
    for module_name in sorted(facts.__all__):
        lines = []
        print('--> Doing fact module: {0}'.format(module_name))
        module = getattr(facts, module_name)

        full_title = '{0} Facts'.format(module_name.title())
        lines.append(full_title)
        lines.append(_title_line('-', full_title))
        lines.append('')

        fact_classes = [
            (key, value)
            for key, value in getmembers(module)
            if (
                isclass(value)
                and (issubclass(value, FactBase) or issubclass(value, ShortFactBase))
                and value.__module__ == module.__name__
                and value is not FactBase
                and not value.__name__.endswith('Base')  # hacky!
            )
        ]

        for fact, cls in fact_classes:
            # FactClass -> fact_accessor on host object
            name = fact
            args_string_and_brackets = ''

            # Does this fact take args?
            command_attr = getattr(cls, 'command', None)
            if isinstance(command_attr, (FunctionType, MethodType)):
                # Attach basic argspec to name
                # Note only supports facts with one arg as this is all that's
                # possible, will need to refactor to print properly in future.
                argspec = getargspec(command_attr)

                arg_defaults = [
                    "'{}'".format(arg) if isinstance(arg, six.string_types) else arg
                    for arg in argspec.defaults
                ] if argspec.defaults else None

                # Create a dict of arg name -> default
                defaults = dict(zip(
                    argspec.args[-len(arg_defaults):],
                    arg_defaults,
                )) if arg_defaults else {}

                if len(argspec.args):
                    args_string_and_brackets = ', {0}'.format(', '.join(
                        (
                            '{0}={1}'.format(arg, defaults.get(arg))
                            if arg in defaults
                            else arg
                        )
                        for arg in argspec.args
                        if arg != 'self'
                    ))

            title = ':code:`{0}.{1}`'.format(module_name, name)
            lines.append(title)

            # Underline name with -'s for title
            lines.append(_title_line('~', title))
            lines.append('')

            # Attach the code block
            lines.append('''
.. code:: python

    host.get_fact({1}{2})

'''.strip().format(module_name, name, args_string_and_brackets))

            # Append any docstring
            doc = cls.__doc__
            if doc:
                lines.append('')
                lines.append('{0}'.format('\n'.join([
                    line[4:] for line in doc.split('\n')
                ])))

            lines.append('')
            lines.append('')

        # Write out the file
        module_filename = path.join(docs_dir, 'facts', '{0}.rst'.format(module_name))
        print('--> Writing {0}'.format(module_filename))

        out = '\n'.join(lines)

        with open(module_filename, 'w') as outfile:
            outfile.write(out)


if __name__ == '__main__':
    print('### Building fact docs')
    build_facts()
