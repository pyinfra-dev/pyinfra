import inspect
import os
import tempfile
from io import BytesIO, StringIO
from unittest import TestCase

from jinja2 import DictLoader, Undefined

from pyinfra.api.util import (
    format_exception,
    get_caller_frameinfo,
    get_file_io,
    get_template,
    try_int,
)


class TestApiUtil(TestCase):
    def test_try_int_number(self):
        assert try_int("1") == 1

    def test_try_int_fail(self):
        assert try_int("hello") == "hello"

    def test_get_caller_frameinfo(self):
        def _get_caller_frameinfo():
            return get_caller_frameinfo()

        frame = inspect.currentframe()
        assert frame is not None
        frameinfo = _get_caller_frameinfo()
        assert frameinfo.lineno == frame.f_lineno - 1  # called by the line above

    def test_format_exception(self):
        exception = Exception("I am a message", 1)
        assert format_exception(exception) == "Exception('I am a message', 1)"


def test_template_registrations_and_imports():
    options = {
        "loader": DictLoader({"child": "{{ label(value)|shout }}:{{ value is positive }}"}),
    }
    filters = {"shout": str.upper}
    globals_ = {"label": str, "value": 3}
    tests = {"positive": lambda value: value > 0}
    template = get_template(
        StringIO('{% import "child" as child without context %}{{ child }}:{{ [1, 2]|length }}'),
        options,
        filters,
        globals_,
        tests,
    )
    assert template.render() == "3:True:2"
    assert "loader" in options
    assert filters == {"shout": str.upper}
    assert globals_ == {"label": str, "value": 3}
    assert set(tests) == {"positive"}
    assert template.render(value=-1) == "3:True:2"  # import without context uses globals


def test_template_environment_defaults_can_be_overridden():
    template = get_template(
        StringIO("{{ missing }}\n"), {"undefined": Undefined, "keep_trailing_newline": False}
    )
    assert template.render() == ""


def test_template_loader_registers_before_loading():
    options = {"loader": DictLoader({"custom.j2": "{{ value|shout }}:{{ value is string }}"})}
    for value in ("first", "second"):
        template = get_template(
            "custom.j2",
            options,
            jinja_filters={"shout": str.upper},
            jinja_globals={"value": value},
            jinja_tests={"string": lambda value: False},
        )
        assert template.render() == f"{value.upper()}:False"
    assert "loader" in options


def test_template_cache_isolates_customizations(tmp_path):
    source = tmp_path / "template.j2"
    source.write_text("{{ value|upper }}:{{ value is string }}")
    filename = str(source)
    default = get_template(filename)
    assert default.render(value="hello") == "HELLO:True"
    for result in ("first", "second"):
        custom = get_template(
            filename,
            jinja_filters={"upper": lambda value: value[0]},
            jinja_globals={"value": [result]},
            jinja_tests={"string": lambda value: False},
        )
        assert custom.render() == f"{result}:False"
    assert get_template(filename) is default
    assert default.render(value="hello") == "HELLO:True"


def test_template_cache_isolates_environment_options(tmp_path):
    source = tmp_path / "options.j2"
    source.write_text("[[ value ]]\n")
    filename = str(source)
    assert (
        get_template(
            filename,
            {
                "variable_start_string": "[[",
                "variable_end_string": "]]",
                "keep_trailing_newline": False,
            },
        ).render(value="custom")
        == "custom"
    )
    assert get_template(filename).render(value="default") == "[[ value ]]\n"


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

    def test_get_file_io_filename_to_string_is_utf8(self):
        text = "café (◕‿◕✿) 🆔"
        with tempfile.NamedTemporaryFile("wb", delete=False) as file:
            file.write(text.encode("utf-8"))

        try:
            with get_file_io(file.name, mode="r") as f:
                data = f.read()
        finally:
            os.unlink(file.name)

        assert data == text


class TestGetTemplateLoader(TestCase):
    def test_get_template_uses_custom_loader_search_path(self):
        import os
        import tempfile

        import jinja2

        from pyinfra.api.util import TEMPLATES, get_template

        TEMPLATES.clear()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fstab")
            with open(path, "w", encoding="utf-8") as f:
                f.write("device {{ mount }}\n")

            # Name is not a path under cwd; the loader must find it.
            template = get_template("fstab", {"loader": jinja2.FileSystemLoader([tmp])})
            assert template.render(mount="/") == "device /\n"

    def test_get_template_still_reads_an_existing_file_path(self):
        import os
        import tempfile

        from pyinfra.api.util import TEMPLATES, get_template

        TEMPLATES.clear()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "motd.j2")
            with open(path, "w", encoding="utf-8") as f:
                f.write("hello {{ name }}")

            template = get_template(path)
            assert template.render(name="world") == "hello world"

    def test_get_template_prefers_existing_path_over_loader_search(self):
        import os
        import tempfile

        import jinja2

        from pyinfra.api.util import TEMPLATES, get_template

        TEMPLATES.clear()
        with tempfile.TemporaryDirectory() as tmp:
            existing = os.path.join(tmp, "motd.j2")
            with open(existing, "w", encoding="utf-8") as f:
                f.write("from-file")
            search = os.path.join(tmp, "search")
            os.mkdir(search)
            with open(os.path.join(search, "motd.j2"), "w", encoding="utf-8") as f:
                f.write("from-loader")

            # Existing path is still read directly so include/extends loaders keep working.
            template = get_template(existing, {"loader": jinja2.FileSystemLoader([search])})
            assert template.render() == "from-file"
