from unittest import TestCase
from pyinfra.api import HiddenValue
import copy


class OtherHiddenValue(HiddenValue):
    """Subclass of HiddenValue to validate basic usage"""

    def __init__(self, service: str = "", username: str = "") -> None:
        super().__init__("fake_value", masked_value="FAKE NEWS")
        self.__service = service
        self.__username = username

    def unmask(self) -> str:
        return self.__service + self.__username


class TestHiddenValue(TestCase):
    def test_hidden(self):
        s = HiddenValue("top secret")
        assert str(s) == "*MASKED*"
        assert repr(s) == "'*MASKED*'"
        assert s.unmask() == "top secret"

    def test_deepcopy(self):
        s = HiddenValue("12345")
        new_s = copy.deepcopy(s)
        assert new_s.unmask() == "12345"
        assert str(new_s) == "*MASKED*"

    def test_deepcopy_subclass(self):
        s = OtherHiddenValue(service="ssh", username="pyinfra")
        new_s = copy.deepcopy(s)
        assert isinstance(new_s, OtherHiddenValue)
        assert new_s.unmask() == "sshpyinfra"
        assert str(new_s) == "FAKE NEWS"
