# pyinfra
# File: pyinfra/api/host.py
# Desc: thin class that represents a target host in pyinfra, also creates classmodule on pyinfra.host
#       which updates to the "current host" in-deploy

import sys

import pyinfra
from pyinfra import state

from .facts import is_fact, get_fact
from .attrs import FallbackAttrData, wrap_attr_data


class Host(object):
    '''Represents a target host. Thin class that links up to facts and host/group data.'''
    _data = None

    @property
    def data(self):
        if not self._data:
            self._data = FallbackAttrData(
                state.inventory.get_host_data(self.ssh_hostname),
                state.inventory.get_groups_data(self.groups),
                state.inventory.get_data(),
                state.inventory.get_default_data()
            )

        return self._data

    @property
    def host_data(self):
        return state.inventory.get_host_data(self.ssh_hostname)

    @property
    def group_data(self):
        return state.inventory.get_groups_data(self.groups)

    def __init__(self, ssh_hostname, groups=None):
        self.ssh_hostname = ssh_hostname
        self.groups = groups if groups else []

    def __getattr__(self, key):
        if not is_fact(key):
            raise AttributeError('No such fact: {}'.format(key))

        fact = get_fact(self.ssh_hostname, key)
        return wrap_attr_data(key, fact)


class HostModule(object):
    '''
    A classmodule which binds to pyinfra.host. At any time inside a pyinfra deploy, pyinfra.host can
    be set to any Host object above via this classmodule's set method.
    '''
    def set(self, host):
        self.host = host
        self.ssh_hostname = host.ssh_hostname
        self.groups = host.groups
        self.data = host.data
        self.host_data = host.host_data
        self.group_data = host.group_data

    def __getattr__(self, key):
        return getattr(self.host, key)

sys.modules['pyinfra.host'] = pyinfra.host = HostModule()
