# pyinfra
# File: pyinfra/api/host.py
# Desc: thin class that represents a target host in pyinfra, also creates classmodule on
#       pyinfra.host which updates to the "current host" in-deploy

import sys

from .facts import is_fact, get_fact
from .attrs import FallbackAttrData, wrap_attr_data


class Host(object):
    '''Represents a target host. Thin class that links up to facts and host/group data.'''
    _data = None

    @property
    def data(self):
        if not self._data:
            self._data = FallbackAttrData(
                self.inventory.get_override_data(),
                self.inventory.get_host_data(self.ssh_hostname),
                self.inventory.get_groups_data(self.groups),
                self.inventory.get_data()
            )

        return self._data

    @property
    def host_data(self):
        return self.inventory.get_host_data(self.ssh_hostname)

    @property
    def group_data(self):
        return self.inventory.get_groups_data(self.groups)

    def __init__(self, inventory, ssh_hostname, groups=None):
        self.inventory = inventory
        self.ssh_hostname = ssh_hostname
        self.groups = groups if groups else []

    def __getattr__(self, key):
        if not is_fact(key):
            raise AttributeError('No such fact: {0}'.format(key))

        fact = get_fact(self.inventory.state, self.ssh_hostname, key)
        return wrap_attr_data(key, fact)


class HostModule(object):
    '''
    A classmodule which binds to ``pyinfra.pseudo_host``. Used in CLI deploys as deploy
    files can't access the host themselves. Additionally binds to pyinfra.host as a nicer
    looking alternative for deploy scripts: (``host.data.x`` > ``pseudo_host.data.x``)
    '''
    _host = None

    def __getattr__(self, key):
        return getattr(self._host, key)

    def __setattr__(self, key, value):
        if key == '_host':
            return object.__setattr__(self, key, value)

        setattr(self._host, key, value)

    def set(self, host):
        '''
        Bind a new host object.

        Args:
            host (``pyinfra.api.Host`` obj): host object to bind to
        '''

        self._host = host


import pyinfra
sys.modules['pyinfra.pseudo_host'] = sys.modules['pyinfra.host'] = \
    pyinfra.pseudo_host = pyinfra.host = \
    HostModule()
