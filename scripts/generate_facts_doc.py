#!/usr/bin/env python

# pyinfra
# File: docs/generate_fact_docs.py
# Desc: generate rst docs from the fact classes

from inspect import getargspec, getmembers, isclass
from types import MethodType

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
            if isinstance(command_attr, MethodType):
                # Attach basic argspec to name
                # Note only supports facts with one arg as this is all that's possible,
                # will need to refactor to print properly in future.
                argspec = getargspec(command_attr)
                if len(argspec.args) > 1:
                    name = '{0}({1})'.format(
                        name,
                        ', '.join(arg for arg in argspec.args if arg != 'self'),
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
