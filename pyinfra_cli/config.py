# pyinfra
# File: pyinfra/cli/config.py
# Desc: config handling for the CLI

from os import path

import six

from pyinfra.api import Config
from pyinfra.api.util import exec_file


def load_config(deploy_dir):
    '''
    Loads any local config.py file.
    '''

    config = Config()
    config_filename = path.join(deploy_dir, 'config.py')

    if path.exists(config_filename):
        attrs = exec_file(config_filename, return_locals=True)

        for key, value in six.iteritems(attrs):
            if hasattr(config, key):
                setattr(config, key, value)

    return config


def load_deploy_config(deploy_filename, config):
    '''
    Loads any local config overrides in the deploy file.
    '''

    if not deploy_filename:
        return

    if path.exists(deploy_filename):
        attrs = exec_file(deploy_filename, return_locals=True)

        for key, value in six.iteritems(attrs):
            if hasattr(config, key):
                setattr(config, key, value)

    return config
