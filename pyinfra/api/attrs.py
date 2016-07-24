# pyinfra
# File: pyinfra/api/attrs.py
# Desc: helpers to manage "wrapped attributes"

'''
This file contains helpers/classes which allow us to have base type (``str``, ``int``, etc)
like operation arguments while also being able to keep track of the original reference (ie
the ``x`` in ``host.data.x``). This means we can generate one operation hash based on an
argument ``host.data.x`` where ``host.data.x`` changes between hosts. The same logic is
applied to facts.
'''

import six


def wrap_attr_data(key, attr):
    '''
    Wraps an object (hopefully) as a AttrBase item.
    '''

    if isinstance(attr, bool):
        return AttrDataBool(key, attr)

    if isinstance(attr, six.string_types):
        return AttrDataStr(key, attr)

    if isinstance(attr, int):
        return AttrDataInt(key, attr)

    return attr


class AttrBase:
    '''
    Subclasses of this represent core Python types with an extra 'host_key' attribute.
    '''

    pyinfra_attr_key = None


class AttrDataStr(AttrBase, six.text_type):
    def __new__(cls, key, obj):
        obj = super(AttrDataStr, cls).__new__(cls, obj)
        setattr(obj, 'pyinfra_attr_key', key)
        return obj


class AttrDataInt(AttrBase, int):
    def __new__(cls, key, obj):
        obj = super(AttrDataInt, cls).__new__(cls, obj)
        setattr(obj, 'pyinfra_attr_key', key)
        return obj


class AttrDataBool(AttrBase, int):
    def __new__(cls, key, obj):
        obj = super(AttrDataBool, cls).__new__(cls, bool(obj))
        setattr(obj, 'pyinfra_attr_key', key)
        return obj


class AttrData(object):
    '''
    Dict with attribute access and AttrBase wrappers.
    '''

    def __init__(self, attrs):
        self.attrs = attrs

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, key):
        return self.get(key)

    def __contains__(self, key):
        return key in self.attrs

    def __str__(self):
        return six.text_type(self.attrs)

    def get(self, key):
        return wrap_attr_data(key, self.attrs.get(key))

    def dict(self):
        return self.attrs


class FallbackAttrData(object):
    '''
    Combines multiple AttrData's to search for attributes.
    '''

    def __init__(self, *datas):
        self.datas = datas

    def __getattr__(self, key):
        for data in self.datas:
            if key in data:
                return data[key]

    def __str__(self):
        return six.text_type(self.datas)

    def dict(self):
        out = {}

        # Copy and reverse data objects
        datas = list(self.datas)
        datas.reverse()

        for data in datas:
            out.update(data.dict())

        return out
