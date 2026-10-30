import copy
from io import StringIO
from unittest import TestCase

import pytest

from pyinfra.api import HiddenValue
from pyinfra.api.util import get_template


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

    def test_nested(self):
        """A HiddenValue wrapped in another one is not the mask, it is the value."""
        s = HiddenValue(HiddenValue("top secret"))
        assert str(s) == "*MASKED*"
        assert s.unmask() == "top secret"

    def test_nested_subclass(self):
        """Unwrapping goes through the subclass's own unmask(), wherever it draws its value from."""
        s = HiddenValue(OtherHiddenValue(service="ssh", username="pyinfra"))
        assert str(s) == "*MASKED*"
        assert s.unmask() == "sshpyinfra"

    def test_nested_several_deep(self):
        s = HiddenValue(HiddenValue(HiddenValue("deep")))
        assert s.unmask() == "deep"

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


@pytest.mark.parametrize("jinja_env_kwargs", [None, {}, {"finalize": None}])
def test_template_unmasks_hidden_values(jinja_env_kwargs):
    secret = HiddenValue("top secret")
    template = get_template(
        StringIO("{{ secret }}|{{ config.secret }}|{{ secrets[0] }}|{{ ordinary }}"),
        jinja_env_kwargs,
    )

    assert (
        template.render(
            secret=secret,
            config={"secret": secret},
            secrets=[secret],
            ordinary="public",
        )
        == "top secret|top secret|top secret|public"
    )
    assert str(secret) == "*MASKED*"


def test_template_preserves_explicit_unmask():
    template = get_template(StringIO("{{ secret.unmask() }}"))

    assert template.render(secret=HiddenValue("top secret")) == "top secret"


def test_template_custom_finalize_receives_hidden_value():
    secret = HiddenValue("top secret")
    received = []

    def finalize(value):
        received.append(value)
        return value.unmask().upper()

    template = get_template(StringIO("{{ secret }}"), {"finalize": finalize})

    assert template.render(secret=secret) == "TOP SECRET"
    assert received == [secret]


def test_template_custom_finalize_can_preserve_mask():
    template = get_template(StringIO("{{ secret }}"), {"finalize": str})

    assert template.render(secret=HiddenValue("top secret")) == "*MASKED*"


def test_template_custom_finalize_handles_ordinary_values():
    template = get_template(
        StringIO("{{ value }}|{{ other }}"),
        {"finalize": lambda value: "" if value is None else value},
    )

    assert template.render(value=None, other="public") == "|public"


def test_template_unmasks_custom_finalize_result():
    template = get_template(StringIO("{{ value }}"), {"finalize": HiddenValue})

    assert template.render(value="top secret") == "top secret"


def test_template_options_can_be_reused():
    options = {"finalize": lambda value: f"[{value}]"}
    original_options = options.copy()

    first_template = get_template(StringIO("first:{{ value }}"), options)

    assert first_template.render(value="hello") == "first:[hello]"
    assert options == original_options

    second_template = get_template(StringIO("second:{{ value }}"), options)

    assert second_template.render(value="hello") == "second:[hello]"
    assert options == original_options
