from __future__ import print_function

from unittest import TestCase

try:
    from pathlib import Path
    HAS_FSPATH = hasattr(Path, '__fspath__')
except ImportError:
    HAS_FSPATH = False

import pytest

from pyinfra.operations.util.compat import fspath


class TestCompatFSPath(TestCase):

    def test_fspath(self):
        assert '/path/to/file' == fspath('/path/to/file')
        with pytest.raises(TypeError):
            _ = fspath(100)

        class DummyPathLike(object):
            def __init__(self, path):
                self._path = path

            @classmethod
            def __fspath__(cls, obj):
                return obj._path

        assert '/path/to/file' == fspath(DummyPathLike('/path/to/file'))

        class FakePathLike_1(object):
            def __init__(self, path):
                self._path = path

            @classmethod
            def __fspath__(cls, obj):
                return len(obj._path)

        with pytest.raises(TypeError):
            _ = fspath(FakePathLike_1('/path/to/file'))

        class FakePathLike_2(object):
            def __init__(self, path):
                self._path = path

            @classmethod
            def __fspath__(cls, obj):
                raise NotImplementedError

        with pytest.raises(NotImplementedError):
            _ = fspath(FakePathLike_2('/path/to/file'))

        class FakePathLike_3(object):
            def __init__(self, path):
                self._path = path

            @classmethod
            def __fspath__(cls, obj):
                return obj._path.non_valid_attribute

        with pytest.raises(AttributeError):
            _ = fspath(FakePathLike_3('/path/to/file'))

    @pytest.mark.skipif(
        not HAS_FSPATH,
        reason='requires Python 3.6+ (pathlib module + __fspath__)',
    )
    def test_fspath_with_pathlib_object(self):
        assert '/path/to/file' == fspath(Path('/path/to/file'))
