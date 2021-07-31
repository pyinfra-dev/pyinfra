import ast

import six

from pyinfra import logger
from pyinfra.api.config import config_defaults


def extract_file_config(filename, config=None):
    with open(filename, 'r') as f:
        data = f.read()

    ast_data = ast.parse(data, filename=filename)
    config_data = {}

    for node in ast_data.body:
        if not isinstance(node, ast.Assign):
            continue

        # Named Python objects (e.g. True/False/None)
        if isinstance(node.value, ast.Name):
            if node.value.id == 'True':
                value = True
            elif node.value.id == 'False':
                value = False
            else:
                value = None

        # NameConstant is Python 3+ only
        elif six.PY3 and isinstance(node.value, ast.NameConstant):
            value = node.value.value

        # Strings
        elif isinstance(node.value, ast.Str):
            value = node.value.s

        # Integers
        elif isinstance(node.value, ast.Num):
            value = node.value.n

        # Config cannot be anything else
        else:
            continue

        # If one of the assignments matches a config variable (e.g. SUDO = True)
        # then assign it to the config object!
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id.isupper() and target.id in config_defaults:
                logger.warning((
                    'file: {0}\n\tDefining config variables directly is deprecated, '
                    'please use `config.{1} = {2}`.'
                ).format(filename, target.id, repr(value)))
                config_data[target.id] = value

    # If we have a config, update and exit
    if config:
        for key, value in six.iteritems(config_data):
            setattr(config, key, value)
        return

    return config_data
