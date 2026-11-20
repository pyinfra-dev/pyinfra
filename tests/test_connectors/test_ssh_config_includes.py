from unittest.mock import patch

import pytest

from pyinfra.connectors.sshuserclient.config import SSHConfig


@pytest.mark.parametrize("separator", [" ", "\t"])
def test_multiple_include_patterns(tmp_path, separator):
    hosts = tmp_path / "hosts"
    hosts.mkdir()
    nested = hosts / "site_b"
    nested.mkdir()
    (hosts / "site_a.conf").write_text("Host site_a\n HostName a.example\n", encoding="utf-8")
    (nested / "site_b.conf").write_text("Host site_b\n Port 2222\n", encoding="utf-8")
    config_file = tmp_path / "config"
    config_file.write_text(f"Include hosts/*.conf{separator}hosts/*/*.conf\n", encoding="utf-8")
    with config_file.open(encoding="utf-8") as stream:
        config = SSHConfig.from_file(stream)
    assert config.lookup("site_a")["hostname"] == "a.example"
    assert config.lookup("site_b")["port"] == "2222"


def test_quoted_include_and_pattern_order(tmp_path):
    first = tmp_path / "first config"
    first.write_text("Host target\n User first\n", encoding="utf-8")
    second = tmp_path / "second"
    second.write_text("Host target\n User second\n Port 2222\n", encoding="utf-8")
    config_file = tmp_path / "config"
    config_file.write_text('Include "first config" missing* second # comment\n', encoding="utf-8")
    with config_file.open(encoding="utf-8") as stream:
        config = SSHConfig.from_file(stream)
    assert config.lookup("target")["user"] == "first"
    assert config.lookup("target")["port"] == "2222"


def test_include_glob_lexical_order(tmp_path):
    first = tmp_path / "10-first.conf"
    second = tmp_path / "20-second.conf"
    first.write_text("Host target\n User first\n", encoding="utf-8")
    second.write_text("Host target\n User second\n", encoding="utf-8")
    config_file = tmp_path / "config"
    config_file.write_text("Include *.conf\n", encoding="utf-8")
    with patch(
        "pyinfra.connectors.sshuserclient.config.glob.iglob",
        return_value=iter([str(second), str(first)]),
    ):
        with config_file.open(encoding="utf-8") as stream:
            config = SSHConfig.from_file(stream)
    assert config.lookup("target")["user"] == "first"
