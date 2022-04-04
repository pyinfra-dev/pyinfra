#!/usr/bin/env python

from os import path

from pyinfra.api import Config
from pyinfra.api.arguments import OPERATION_KWARGS


def build_arguments_doc():
    pyinfra_config = Config()

    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, '..', 'docs'))

    lines = []

    for category, kwarg_configs in OPERATION_KWARGS.items():
        if category is None:
            continue

        lines.append('{0}'.format(category))
        lines.append(''.join('~' for _ in range(len(category))))
        lines.append('')

        for key, config in kwarg_configs.items():
            description = config
            if isinstance(config, dict):
                description = config.get('description')
                default = config.get('default')
                if callable(default):
                    default = default(pyinfra_config)
                if default is not None:
                    key = '{0}={1}'.format(key, default)

            lines.append('+ ``{0}``: {1}'.format(key, description))

    module_filename = path.join(docs_dir, '_deploy_globals.rst')
    print('--> Writing {0}'.format(module_filename))

    out = '\n'.join(lines)

    with open(module_filename, 'w') as outfile:
        outfile.write(out)


if __name__ == '__main__':
    print('### Building arguments doc')
    build_arguments_doc()
