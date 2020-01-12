import ast

from os import path

import six

from pyinfra.api import Config

from .util import exec_file


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
            if target.id.isupper() and hasattr(Config, target.id):
                config_data[target.id] = value

    # If we have a config, update and exit
    if config:
        for key, value in six.iteritems(config_data):
            setattr(config, key, value)
        return

    return config_data


def load_config(deploy_dir):
    '''
    Loads any local config.py file.
    '''

    config = Config()
    config_filename = path.join(deploy_dir, 'config.py')

    if path.exists(config_filename):
        extract_file_config(config_filename, config)

        # Now execute the file to trigger loading of any hooks
        exec_file(config_filename)

    return config


def load_deploy_config(deploy_filename, config=None):
    '''
    Loads any local config overrides in the deploy file.
    '''

    if not config:
        config = Config()

    if not deploy_filename:
        return

    if path.exists(deploy_filename):
        extract_file_config(deploy_filename, config)

    return config
