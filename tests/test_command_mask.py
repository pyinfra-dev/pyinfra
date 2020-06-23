from __future__ import print_function

from unittest import TestCase

from pyinfra.api import StringCommand, Mask


class TestCommandMask(TestCase):

	def test_mask(self):
		ts = Mask("adsfg")
		assert hasattr(ts, "hide_me")

	def test_one(self):
		ts = StringCommand.join([Mask("adsfg")])

		assert str(ts) == "adsfg"
		assert getattr(ts, "masked") == "***"

	def test_two(self):
		ts = StringCommand.join(["some", "stuff", Mask("mask me"), "other", "stuff"])

		assert str(ts) == "some stuff mask me other stuff"
		assert getattr(ts, "masked") == "some stuff *** other stuff"
