import os
import sys
from datetime import datetime, timezone
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

import pytest

from pyinfra.operations import server
from pyinfra_cli.commands import get_func_and_args
from pyinfra_cli.exceptions import CliError
from pyinfra_cli.util import (
    fetch_remote_deploy_file,
    is_remote_url,
    json_encode,
    try_import_module_attribute,
)


class TestCliUtil(TestCase):
    def test_json_encode_function(self):
        assert json_encode(get_func_and_args) == "Function: get_func_and_args"

    def test_json_encode_datetime(self):
        now = datetime.now(timezone.utc)
        assert json_encode(now) == now.isoformat()

    def test_json_encode_file(self):
        file = StringIO()
        assert json_encode(file) == "In memory file: "

    def test_json_encode_set(self):
        assert json_encode({1, 2, 3}) == [1, 2, 3]

    def test_setup_no_module(self):
        with self.assertRaises(CliError) as context:
            get_func_and_args(("no.op",))
        assert context.exception.message == "No such module: no"

    def test_setup_no_op(self):
        with self.assertRaises(CliError) as context:
            get_func_and_args(("server.no",))

        assert context.exception.message == "No such attribute in module server: no"

    def test_setup_op_and_args(self):
        commands = ("pyinfra.operations.server.user", "one", "two", "hello=world")

        assert get_func_and_args(commands) == (
            server.user,
            (["one", "two"], {"hello": "world"}),
        )

    def test_setup_op_and_json_args(self):
        commands = ("server.user", '[["one", "two"], {"hello": "world"}]')

        assert get_func_and_args(commands) == (
            server.user,
            (["one", "two"], {"hello": "world"}),
        )


@pytest.fixture(scope="function")
def user_sys_path():
    user_pkg = os.path.dirname(__file__) + "/user"
    sys.path.append(user_pkg)
    yield None
    sys.path.pop()
    to_rm = []
    for k, v in sys.modules.items():
        v = getattr(v, "__file__", "")
        if isinstance(v, str) and v.startswith(user_pkg):
            to_rm.append(k)
    for k in to_rm:
        del sys.modules[k]


# def test_no_user_op():
#     commands = ('test_ops.dummy_op', 'arg1', 'arg2')
#     with pytest.raises(CliError, match='^No such module: test_ops$'):
#         get_func_and_args(commands)


def test_user_op(user_sys_path):
    commands = ("test_ops.dummy_op", "arg1", "arg2")
    res = get_func_and_args(commands)

    import test_ops

    assert res == (test_ops.dummy_op, (["arg1", "arg2"], {}))


def test_is_remote_url_http_and_https():
    assert is_remote_url("http://example.com/op.py") is True
    assert is_remote_url("https://raw.githubusercontent.com/x/y/main/op.py") is True


def test_is_remote_url_rejects_local_paths_and_other_schemes():
    assert is_remote_url("deploy.py") is False
    assert is_remote_url("/abs/path/deploy.py") is False
    assert is_remote_url("./deploy.py") is False
    assert is_remote_url("file:///tmp/deploy.py") is False
    assert is_remote_url("git+https://example.com/repo") is False


def test_fetch_remote_deploy_file_writes_body_to_temp_py(tmp_path):
    body = b"from pyinfra.operations import server\nserver.shell(commands=['true'])\n"

    class _FakeResp:
        status = 200

        def read(self):
            return body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    with patch("pyinfra_cli.util.urlopen", return_value=_FakeResp()) as mock_urlopen:
        out_path = fetch_remote_deploy_file("https://example.com/op.py")

    assert out_path.endswith(".py")
    assert os.path.basename(out_path).startswith("pyinfra-remote-")
    with open(out_path, "rb") as f:
        assert f.read() == body
    assert mock_urlopen.call_count == 1
    os.unlink(out_path)


def test_fetch_remote_deploy_file_raises_on_non_200():
    class _FakeResp:
        status = 404

        def read(self):
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    with patch("pyinfra_cli.util.urlopen", return_value=_FakeResp()):
        with pytest.raises(CliError, match="HTTP 404"):
            fetch_remote_deploy_file("https://example.com/missing.py")


def test_validate_operations_accepts_remote_url(monkeypatch, tmp_path):
    from pyinfra_cli.cli import CliCommands, _validate_operations

    fake_local = tmp_path / "fetched.py"
    fake_local.write_text("# fetched\n")

    monkeypatch.setattr(
        "pyinfra_cli.cli.fetch_remote_deploy_file",
        lambda url: str(fake_local),
    )

    url = "https://example.com/op.py"
    original, operations, command, chdir = _validate_operations([url], None)

    assert command == CliCommands.DEPLOY_FILES
    assert operations == [str(fake_local)]
    assert original == [url]


def test_validate_operations_mixed_local_and_remote(monkeypatch, tmp_path):
    from pyinfra_cli.cli import CliCommands, _validate_operations

    local = tmp_path / "local.py"
    local.write_text("# local\n")
    fake_remote = tmp_path / "remote.py"
    fake_remote.write_text("# remote\n")

    monkeypatch.setattr(
        "pyinfra_cli.cli.fetch_remote_deploy_file",
        lambda url: str(fake_remote),
    )

    _original, operations, command, _chdir = _validate_operations(
        [str(local), "https://example.com/remote.py"],
        None,
    )

    assert command == CliCommands.DEPLOY_FILES
    assert operations == [str(local), str(fake_remote)]


def test_try_import_module_attribute_falls_through_when_attr_missing(monkeypatch, tmp_path):
    # Regression for pyinfra-dev/pyinfra#1747: when a top-level module that
    # collides with a pyinfra fact/operation is importable but lacks the
    # requested attribute, the bare candidate must not short-circuit the
    # prefixed candidate.
    stub_pip = tmp_path / "pip"
    stub_pip.mkdir()
    (stub_pip / "__init__.py").write_text("")

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "pip", raising=False)

    from pyinfra.facts.pip import Pip3Packages

    result = try_import_module_attribute("pip.Pip3Packages", prefix="pyinfra.facts")

    assert result is Pip3Packages


def test_try_import_module_attribute_preserves_windows_path_in_error():
    with pytest.raises(CliError, match=r"^No such module: D:/non_existing_script\.py$"):
        try_import_module_attribute("D:/non_existing_script.py")

    with pytest.raises(CliError, match=r"^No such module: D:\\non_existing_script\.py$"):
        try_import_module_attribute(r"D:\non_existing_script.py")
