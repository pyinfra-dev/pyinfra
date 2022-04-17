from unittest import TestCase

from pyinfra.operations.util.files import unix_path_join


class TestUnixPathJoin(TestCase):
    def test_simple_path(self):
        assert unix_path_join("home", "pyinfra") == "home/pyinfra"

    def test_absolute_path(self):
        assert unix_path_join("/", "home", "pyinfra") == "/home/pyinfra"

    def test_multiple_slash_path(self):
        assert unix_path_join("/", "home/", "pyinfra") == "/home/pyinfra"

    def test_end_slash_path(self):
        assert unix_path_join("/", "home", "pyinfra/") == "/home/pyinfra/"
