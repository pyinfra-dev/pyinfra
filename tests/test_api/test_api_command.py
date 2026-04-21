from unittest import TestCase

try:
    from pathlib import PurePosixPath

    HAS_PATHLIB = True
except ImportError:
    HAS_PATHLIB = False

import pytest

from pyinfra.api import (
    FileDownloadCommand,
    FileUploadCommand,
    FunctionCommand,
    MaskString,
    QuoteString,
    RsyncCommand,
    StringCommand,
)
from pyinfra.api.command import PyinfraCommand, make_formatted_string_command


class TestBaseCommand(TestCase):
    def test_base_command_no_execute(self):
        cmd = PyinfraCommand()
        with self.assertRaises(NotImplementedError):
            cmd.execute(None, None, None)


class TestStringCommand(TestCase):
    def test_normal(self):
        cmd = StringCommand("hello", "world")
        assert str(cmd) == cmd.get_raw_value() == "hello world"

    def test_masked(self):
        cmd = StringCommand(MaskString("adsfg"))
        assert cmd.get_raw_value() == "adsfg"
        assert str(cmd) == "***"

    def test_mixed_masked(self):
        cmd = StringCommand("some", "stuff", MaskString("mask me"), "other", "stuff")
        assert cmd.get_raw_value() == "some stuff mask me other stuff"
        assert str(cmd) == "some stuff *** other stuff"

    def test_nested(self):
        nested_cmd = StringCommand("some", "stuff")
        cmd = StringCommand("hello", nested_cmd, "world")
        assert str(cmd) == cmd.get_raw_value() == "hello some stuff world"

    def test_quote(self):
        quoted_str = QuoteString("quote me!")
        cmd = StringCommand("hello", quoted_str)
        assert str(cmd) == cmd.get_raw_value() == "hello 'quote me!'"

    def test_eq(self):
        assert StringCommand("hello world") == StringCommand("hello world")
        with self.assertRaises(AssertionError):
            assert StringCommand("a") == StringCommand("b")

    def test_separator(self):
        cmd = StringCommand("hello world", "yes", _separator="")
        assert str(cmd) == "hello worldyes"

    def test_int(self):
        cmd = StringCommand("hello", "world", 4420)
        assert str(cmd) == "hello world 4420"

    def test_list(self):
        cmd = StringCommand("hello", "world", ["a", "b", "c"])
        assert str(cmd) == "hello world ['a', 'b', 'c']"

    @pytest.mark.skipif(
        not HAS_PATHLIB,
        reason="Requires Python 3.4+ (pathlib module)",
    )
    def test_path(self):
        cmd = StringCommand("hello", "world", PurePosixPath("/path/to/somewhere"))
        assert str(cmd) == "hello world /path/to/somewhere"


class TestFileCommands(TestCase):
    def test_file_upload_command_repr(self):
        cmd = FileUploadCommand("src", "dest")
        assert repr(cmd) == "FileUploadCommand(src, dest)"

    def test_file_download_command_repr(self):
        cmd = FileDownloadCommand("src", "dest")
        assert repr(cmd) == "FileDownloadCommand(src, dest)"

    def test_rsync_command_repr(self):
        cmd = RsyncCommand("src", "dest", ["-a"])
        assert repr(cmd) == "RsyncCommand(src, dest, ['-a'])"


class TestMakeFormattedStringCommand(TestCase):
    def test_basic_formatting(self):
        cmd = make_formatted_string_command("echo {0}", "hello")
        assert str(cmd) == "echo hello"

    def test_adjacent_args_no_extra_spaces(self):
        """Regression test for https://github.com/pyinfra-dev/pyinfra/issues/1603"""
        cmd = make_formatted_string_command("cat /{0}/{1}", "etc", "passwd")
        assert str(cmd) == "cat /etc/passwd"

    def test_adjacent_args_no_literal_separator(self):
        cmd = make_formatted_string_command("{0}{1}", "hello", "world")
        assert str(cmd) == "helloworld"

    def test_prefix_with_arg(self):
        cmd = make_formatted_string_command("prefix{0}", "value")
        assert str(cmd) == "prefixvalue"

    def test_arg_with_suffix(self):
        cmd = make_formatted_string_command("{0}.txt", "myfile")
        assert str(cmd) == "myfile.txt"

    def test_multiple_separate_args(self):
        cmd = make_formatted_string_command("curl -sSLf {0} -o {1}", "http://example.com", "/tmp/f")
        assert str(cmd) == "curl -sSLf http://example.com -o /tmp/f"

    def test_kwargs(self):
        cmd = make_formatted_string_command("echo {msg}", msg="hello")
        assert str(cmd) == "echo hello"

    def test_quoted_arg(self):
        cmd = make_formatted_string_command("echo {0}", QuoteString("hello world"))
        assert str(cmd) == "echo 'hello world'"

    def test_masked_arg(self):
        cmd = make_formatted_string_command("echo {0}", MaskString("secret"))
        assert cmd.get_raw_value() == "echo secret"
        assert str(cmd) == "echo ***"

    def test_path_with_multiple_segments(self):
        cmd = make_formatted_string_command("ls /{0}/{1}/{2}", "home", "user", "docs")
        assert str(cmd) == "ls /home/user/docs"


class TestFunctionCommand(TestCase):
    def test_function_command_repr(self):
        def some_function():
            pass

        cmd = FunctionCommand(some_function, (), {})
        assert repr(cmd) == "FunctionCommand(some_function, (), {})"
