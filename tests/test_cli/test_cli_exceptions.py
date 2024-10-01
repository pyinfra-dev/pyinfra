import sys
from os import path
from unittest import TestCase

import pytest
from click.testing import CliRunner

from pyinfra.api import OperationError
from pyinfra.api.exceptions import ArgumentTypeError
from pyinfra_cli.exceptions import CliError, UnexpectedExternalError, WrappedError
from pyinfra_cli.main import cli

from .util import run_cli


class TestCliExceptions(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = CliRunner()

    def assert_cli_exception(self, args, message):
        result = self.runner.invoke(cli, args, standalone_mode=False)
        self.assertIsInstance(result.exception, CliError)
        assert getattr(result.exception, "message") == message

    def test_bad_deploy_file(self):
        self.assert_cli_exception(
            ["my-server.net", "nop.py"],
            "No deploy file: nop.py",
        )

    def test_invalid_fact(self):
        self.assert_cli_exception(
            ["my-server.net", "fact", "thing"],
            "Invalid fact: `thing`, should be in the format `module.cls`",
        )

    def test_no_fact_module(self):
        self.assert_cli_exception(
            ["my-server.net", "fact", "not_a_module.SomeFact"],
            "No such module: not_a_module",
        )

    def test_no_fact_cls(self):
        self.assert_cli_exception(
            ["my-server.net", "fact", "server.NotAFact"],
            "No such attribute in module server: NotAFact",
        )


class TestCliDeployExceptions(TestCase):
    def _run_cli(self, hosts, filename):
        return run_cli(
            "-y",
            ",".join(hosts),
            path.join("tests", "test_cli", "deploy_fails", filename),
            f'--chdir={path.join("tests", "test_cli", "deploy_fails")}',
        )

    def test_invalid_argument_type(self):
        result = self._run_cli(["@local"], "invalid_argument_type.py")
        assert isinstance(result.exception, WrappedError)
        assert isinstance(result.exception.exception, ArgumentTypeError)
        assert (
            result.exception.exception.args[0]
            == "Invalid argument `_sudo`:: None is not an instance of bool"
        )

    def test_invalid_operation_arg(self):
        result = self._run_cli(["@local"], "invalid_operation_arg.py")
        assert isinstance(result.exception, UnexpectedExternalError)
        assert isinstance(result.exception.exception, TypeError)
        assert result.exception.filename == "invalid_operation_arg.py"
        assert result.exception.exception.args[0] == "missing a required argument: 'commands'"

    @pytest.mark.skipif(
        sys.platform.startswith("win"),
        reason="The operation is not compatible with Windows",
    )
    def test_operation_error(self):
        result = self._run_cli(["@local"], "operation_error.py")
        assert isinstance(result.exception, WrappedError)
        assert isinstance(result.exception.exception, OperationError)
        assert (
            result.exception.exception.args[0] == "operation_error.py exists and is not a directory"
        )
