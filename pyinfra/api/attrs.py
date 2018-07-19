# pyinfra
# File: pyinfra/api/attrs.py
# Desc: helpers to manage "wrapped attributes"

'''
This file contains helpers/classes which allow us to have base type (``str``,
``int``, etc) like operation arguments while also being able to keep track of
the original reference (ie the ``x`` in ``host.data.x``). This means we can
generate one operation hash based on an argument ``host.data.x`` where
``host.data.x`` changes between hosts. The same logic is applied to facts.
'''

import six


def extract_callable_datas(datas):
    for data in datas:
        # Support for dynamic data, ie @deploy wrapped data defaults where
        # the data is stored on the state temporarily.
        if callable(data):
            data = data()

        yield data


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

    # Nested items/objects
    if isinstance(attr, list):
        return AttrDataList(key, [
            wrap_attr_data('{0}.{1}'.format(key, i), v)
            for i, v in enumerate(attr)
        ])

    if isinstance(attr, dict):
        return AttrDataDict(key, {
            k: wrap_attr_data('{0}.{1}'.format(key, k), v)
            for k, v in six.iteritems(attr)
        })

    return attr


class AttrBase:
    '''
    Subclasses of this represent core Python types with an extra 'host_key' attribute.
    '''

    pyinfra_attr_key = None


# Base types
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


# Iterable types
class AttrDataList(AttrBase, list):
    def __init__(self, key, obj):
        super(AttrDataList, self).__init__(obj)
        setattr(self, 'pyinfra_attr_key', key)


class AttrDataDict(AttrBase, dict):
    def __init__(self, key, obj):
        obj = super(AttrDataDict, self).__init__(obj)
        setattr(self, 'pyinfra_attr_key', key)


class AttrData(dict):
    '''
    Dict with attribute access and AttrBase wrappers.
    '''

    def __init__(self, attrs=None):
        attrs = attrs or {}

        # Wrap the dict
        attrs = {
            key: wrap_attr_data(key, value)
            for key, value in six.iteritems(attrs)
        }

        super(AttrData, self).__init__(attrs)

    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = wrap_attr_data(key, value)


class FallbackAttrData(object):
    '''
    Combines multiple AttrData's to search for attributes.
    '''

    override_datas = None

    def __init__(self, *datas):
        datas = list(datas)

        # Inject an empty override data so we can assign during deploy
        self.__dict__['override_datas'] = {}
        datas.insert(0, self.override_datas)

        self.__dict__['datas'] = tuple(datas)

    def __getattr__(self, key):
        for data in extract_callable_datas(self.datas):
            if key in data:
                return data[key]

    def __setattr__(self, key, value):
        self.override_datas[key] = wrap_attr_data(key, value)

    def __str__(self):
        return six.text_type(self.datas)

    def dict(self):
        out = {}

        # Copy and reverse data objects (such that the first items override
        # the last, matching __getattr__ output).
        datas = list(self.datas)
        datas.reverse()

        for data in extract_callable_datas(datas):
            out.update(data)

        return out
