# pyinfra
# File: pyinfra_cli/config.py
# Desc: config handling for the CLI

import ast

from os import path

from pyinfra.api import Config
from pyinfra.api.util import exec_file


def _extract_config_assignments(filename, config):
    with open(filename, 'r') as f:
        data = ast.parse(f.read())

    for node in data.body:
        if not isinstance(node, ast.Assign):
            continue

        # Named Python objects (eg True/False/None)
        if isinstance(node.value, ast.Name):
            if node.value.id == 'True':
                value = True
            elif node.value.id == 'False':
                value = False
            else:
                value = None

        # Strings
        elif isinstance(node.value, ast.Str):
            value = node.value.s

        # Integers
        elif isinstance(node.value, ast.Num):
            value = node.value.n

        # Config cannot be anything else
        else:
            continue

        # If one of the assignments matches a config variable (eg SUDO = True)
        # then assign it to the config object!
        for target in node.targets:
            if hasattr(config, target.id):
                setattr(config, target.id, value)


def load_config(deploy_dir):
    '''
    Loads any local config.py file.
    '''

    config = Config()
    config_filename = path.join(deploy_dir, 'config.py')

    if path.exists(config_filename):
        _extract_config_assignments(config_filename, config)

        # Now execute the file to trigger loading of any hooks
        exec_file(config_filename)

    return config


def load_deploy_config(deploy_filename, config):
    '''
    Loads any local config overrides in the deploy file.
    '''

    if not deploy_filename:
        return

    if path.exists(deploy_filename):
        _extract_config_assignments(deploy_filename, config)

    return config
