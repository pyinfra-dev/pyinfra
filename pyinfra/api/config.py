# pyinfra
# File: api/config.py
# Desc: the default config

import sys
import imp

import pyinfra


class Config:
    # % of hosts which have to fail for all operations to stop
    FAIL_PERCENT = None

    # All these can be overridden inside module calls
    SUDO = False
    SUDO_USER = 'root'
    IGNORE_ERRORS = False

    @classmethod
    def load_file(cls, config_file):
        module = imp.load_source('', config_file)

        for attr in dir(module):
            if attr.isupper():
                setattr(cls, attr, getattr(module, attr))

        return cls


# Set pyinfra.config to a Config instance
sys.modules['pyinfra.config'] = pyinfra.config = Config()
