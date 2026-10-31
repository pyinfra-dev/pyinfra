from unittest import TestCase

from pyinfra.facts.openwrt.features import Release, ReleaseRange


class TestReleaseRangeInRange(TestCase):
    STD_RANGE = ReleaseRange(Release(3, 5), Release(11, 12))

    def test_major_in(self):
        assert self.STD_RANGE.contains(Release(5, 4))

    def test_major_below(self):
        assert not self.STD_RANGE.contains(Release(1, 99))

    def test_major_above(self):
        assert not self.STD_RANGE.contains(Release(99, 1))

    def test_major_equal_start_minor_above(self):
        assert self.STD_RANGE.contains(Release(3, 11))

    def test_major_equal_start_minor_equal(self):
        assert self.STD_RANGE.contains(Release(3, 5))

    def test_major_equal_start_minor_below(self):
        assert not self.STD_RANGE.contains(Release(3, 3))

    def test_major_equal_end_minor_above(self):
        assert not self.STD_RANGE.contains(Release(11, 15))

    def test_major_equal_end_minor_equal(self):
        assert self.STD_RANGE.contains(Release(11, 12))

    def test_major_equal_end_minor_below(self):
        assert self.STD_RANGE.contains(Release(11, 11))

    def test_major_below_end_start_none(self):
        assert ReleaseRange(None, Release(11, 12)).contains(Release(0, 0))

    def test_major_equal_end_start_none(self):
        assert ReleaseRange(None, Release(11, 12)).contains(Release(11, 12))

    def test_major_above_end_start_none(self):
        assert not ReleaseRange(None, Release(11, 12)).contains(Release(15, 15))
