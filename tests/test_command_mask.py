from __future__ import print_function

from unittest import TestCase

from pyinfra.api import MaskString, StringCommand


class TestStringCommand(TestCase):
    def test_one(self):
        ts = StringCommand(MaskString('adsfg'))

        assert ts.get_raw_value() == 'adsfg'
        assert str(ts) == '***'

    def test_two(self):
        ts = StringCommand('some', 'stuff', MaskString('mask me'), 'other', 'stuff')

        assert ts.get_raw_value() == 'some stuff mask me other stuff'
        assert str(ts) == 'some stuff *** other stuff'
