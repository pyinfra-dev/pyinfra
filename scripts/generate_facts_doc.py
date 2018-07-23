#!/usr/bin/env python

# pyinfra
# File: docs/generate_fact_docs.py
# Desc: generate rst docs from the fact classes

from inspect import getargspec, getmembers, isclass
from types import FunctionType, MethodType

import six

from six.moves import range

from pyinfra import facts
from pyinfra.api.facts import FactBase
from pyinfra.api.util import underscore


def _title_line(char, string):
    return ''.join(char for _ in range(0, len(string)))


def build_facts():
    lines = []

    # Now we generate a facts.rst describing the use of the facts as:
    # host.data.<snake_case_fact>
    for module_name in facts.__all__:
        print('--> Doing fact module: {0}'.format(module_name))
        module = getattr(facts, module_name)

        lines.append(module_name.title())
        lines.append(_title_line('-', module_name))
        lines.append('')

        fact_classes = [
            (key, value)
            for key, value in getmembers(module)
            if (
                isclass(value)
                and issubclass(value, FactBase)
                and value.__module__ == module.__name__
                and value is not FactBase
            )
        ]

        for fact, cls in fact_classes:
            # FactClass -> fact_accessor on host object
            name = underscore(fact)

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
                    name = '{0}({1})'.format(
                        name,
                        ', '.join(
                            (
                                '{0}={1}'.format(arg, defaults[arg])
                                if arg in defaults
                                else arg
                            )
                            for arg in argspec.args
                            if arg != 'self'
                        ),
                    )

            name = ':code:`{0}`'.format(name)
            lines.append(name)

            # Underline name with -'s for title
            lines.append(_title_line('~', name))

            # Append any docstring
            doc = cls.__doc__
            if doc:
                lines.append('')
                lines.append('{0}'.format('\n'.join([
                    line for line in doc.split('\n')
                ])))

            lines.append('')
            lines.append('')

    # Write out the file
    print('--> Writing docs/facts.rst')

    out = '\n'.join(lines)
    out = '''
Facts Index
===========

.. include:: facts_.rst


{0}
    '''.format(out).strip()

    outfile = open('docs/facts.rst', 'w')
    outfile.write(out)
    outfile.close()


if __name__ == '__main__':
    print('### Building fact docs')
    build_facts()
