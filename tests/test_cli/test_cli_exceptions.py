from unittest import TestCase

from click.testing import CliRunner

from pyinfra_cli.exceptions import CliError
from pyinfra_cli.main import cli


class TestCliExceptions(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_cli = CliRunner()
        cls.old_cli_show = CliError.show

    @classmethod
    def tearDownClass(cls):
        CliError.show = cls.old_cli_show

    def setUp(self):
        self.exception = None
        CliError.show = lambda e: self.capture_cli_error(e)

    def capture_cli_error(self, e):
        self.exception = e
        self.old_cli_show()

    def assert_cli_exception(self, args, message):
        self.test_cli.invoke(cli, args)

        self.assertIsInstance(self.exception, CliError)
        assert self.exception.message == message

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
