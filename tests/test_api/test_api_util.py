from io import BytesIO, StringIO
from unittest import TestCase

from pyinfra.api.util import format_exception, get_caller_frameinfo, get_file_io, try_int


class TestApiUtil(TestCase):
    def test_try_int_number(self):
        assert try_int("1") == 1

    def test_try_int_fail(self):
        assert try_int("hello") == "hello"

    def test_get_caller_frameinfo(self):
        def _get_caller_frameinfo():
            return get_caller_frameinfo()

        frameinfo = _get_caller_frameinfo()
        assert frameinfo.lineno == 18  # called by the line above

    def test_format_exception(self):
        exception = Exception("I am a message", 1)
        assert format_exception(exception) == "Exception('I am a message', 1)"


class TestApiUtilFileIO(TestCase):
    def test_get_file_io_stringio_to_string(self):
        file = StringIO("some string")

        with get_file_io(file, mode="r") as f:
            data = f.read()

        assert isinstance(data, str)
        assert data == "some string"

    def test_get_file_io_stringio_to_bytes(self):
        file = StringIO("some string")

        with get_file_io(file) as f:
            data = f.read()

        assert isinstance(data, bytes)
        assert data == b"some string"

    def test_get_file_io_bytesio_to_bytes(self):
        file = BytesIO(b"some string")

        with get_file_io(file) as f:
            data = f.read()

        assert isinstance(data, bytes)
        assert data == b"some string"

    def test_get_file_io_bytesio_to_string(self):
        file = BytesIO(b"some string")

        with get_file_io(file, mode="r") as f:
            data = f.read()

        assert isinstance(data, str)
        assert data == "some string"


class TestGetTemplateWithLoader(TestCase):
    def test_get_template_uses_custom_loader_search_path(self):
        from pathlib import Path
        import tempfile

        from jinja2 import DictLoader, FileSystemLoader

        from pyinfra.api.util import get_template

        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            (Path(d1) / "first.j2").write_text("from d1: {{ val }}", encoding="utf-8")
            (Path(d2) / "first.j2").write_text("from d2: {{ val }}", encoding="utf-8")
            (Path(d2) / "second.j2").write_text("only d2: {{ val }}", encoding="utf-8")

            loader = FileSystemLoader([d1, d2])
            kwargs = {"loader": loader}

            t1 = get_template("first.j2", kwargs)
            assert t1.render({"val": "ok"}) == "from d1: ok"
            assert "loader" in kwargs

            t2 = get_template("second.j2", kwargs)
            assert t2.render({"val": "yes"}) == "only d2: yes"

        dict_loader = DictLoader({"in_memory.j2": "hello {{ who }}"})
        t3 = get_template("in_memory.j2", {"loader": dict_loader})
        assert t3.render({"who": "world"}) == "hello world"

    def test_files_template_with_custom_loader_does_not_prepend_cwd(self):
        from pathlib import Path
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch

        from jinja2 import FileSystemLoader
        import pytest

        from pyinfra.api import OperationError
        from pyinfra.operations import files

        with tempfile.TemporaryDirectory() as search_dir, tempfile.TemporaryDirectory() as cwd_dir:
            (Path(search_dir) / "motd.j2").write_text("Welcome {{ target }}!", encoding="utf-8")
            (Path(search_dir) / "broken.j2").write_text("{{ missing_var }}", encoding="utf-8")
            loader = FileSystemLoader([search_dir])

            captured = {}

            def fake_put_inner(*args, **kwargs):
                captured["content"] = kwargs["src"].read()
                captured["template"] = getattr(kwargs["src"], "template", None)
                yield "put-cmd"

            fake_state = SimpleNamespace(cwd=cwd_dir, inventory=object())
            with (
                patch.object(files, "state", fake_state),
                patch.object(files.put, "_inner", side_effect=fake_put_inner),
            ):
                cmds = list(
                    files.template._inner(
                        "motd.j2",
                        "/etc/motd",
                        jinja_env_kwargs={"loader": loader},
                        target="pyinfra",
                    )
                )
                assert cmds == ["put-cmd"]
                assert captured["content"] == "Welcome pyinfra!"
                assert captured["template"] == "motd.j2"

                with pytest.raises(OperationError) as exc_info:
                    list(
                        files.template._inner(
                            "broken.j2",
                            "/etc/motd",
                            jinja_env_kwargs={"loader": loader},
                        )
                    )
                assert "Error in template: broken.j2" in str(exc_info.value)
                assert "missing_var" in str(exc_info.value)
