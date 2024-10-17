import pytest

from pyinfra.facts.server import _group_info_from_group_str


def test__group_info_from_group_str() -> None:
    test_str = "plugdev:x:46:sysadmin,user2"
    group_info = _group_info_from_group_str(test_str)

    assert group_info["name"] == "plugdev"
    assert group_info["password"] == "x"
    assert group_info["gid"] == 46
    assert group_info["user_list"] == ["sysadmin", "user2"]


def test__group_info_from_group_str_empty() -> None:
    with pytest.raises(ValueError):
        _group_info_from_group_str("")

    with pytest.raises(ValueError):
        _group_info_from_group_str("a:b:")
