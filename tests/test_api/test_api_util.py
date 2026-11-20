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
