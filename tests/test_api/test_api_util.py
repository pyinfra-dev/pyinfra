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

    def test_get_file_io_binary_write_into_stringio(self):
        # A binary writer (a command's raw stdout) landing in a text destination.
        file = StringIO("stale")

        with get_file_io(file, mode="wb") as f:
            f.write(b"h\xc3\xa9")

        assert file.getvalue() == "hé"

    def test_get_file_io_failed_binary_write_leaves_stringio_intact(self):
        file = StringIO("stale")

        with self.assertRaises(RuntimeError):
            with get_file_io(file, mode="wb") as f:
                f.write(b"partial")
                raise RuntimeError()

        assert file.getvalue() == "stale"
