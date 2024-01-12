from unittest import TestCase

from click.testing import CliRunner

from pyinfra_cli.exceptions import CliError
from pyinfra_cli.main import cli


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
            "No such module: pyinfra.facts.not_a_module",
        )

    def test_no_fact_cls(self):
        self.assert_cli_exception(
            ["my-server.net", "fact", "server.NotAFact"],
            "No such attribute in module pyinfra.facts.server: NotAFact",
        )
