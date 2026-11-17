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

    def test_get_file_io_filename_to_string_is_utf8(self):
        # Imported here: an import at the top would shift the line test_get_caller_frameinfo checks
        import os
        import tempfile

        text = "café ◕‿◕ 🆔"
        with tempfile.NamedTemporaryFile("wb", delete=False) as file:
            file.write(text.encode("utf-8"))

        try:
            with get_file_io(file.name, mode="r") as f:
                data = f.read()
        finally:
            os.unlink(file.name)

        assert data == text
