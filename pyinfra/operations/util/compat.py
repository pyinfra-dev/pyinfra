from __future__ import unicode_literals

import six


# NOTE https://github.com/python/cpython/blob/master/Lib/os.py#L1025
def fspath(path):
    path_types = six.string_types
    path_type_names = [pt.__name__ for pt in path_types]

    if isinstance(path, path_types):
        return path

    path_type = type(path)
    try:
        path_repr = path_type.__fspath__(path)
    except AttributeError:
        if hasattr(path_type, '__fspath__'):
            raise
        else:
            raise TypeError('expected {} or os.PathLike object, '
                            'not {}'.format(','.join(path_type_names), path_type.__name__))

    if isinstance(path_repr, path_types):
        return path_repr
    else:
        raise TypeError('expected {}.__fspath__() to return {} '
                        'not {}'.format(path_type.__name__,
                                        ','.join(path_type_names),
                                        type(path_repr).__name__))
