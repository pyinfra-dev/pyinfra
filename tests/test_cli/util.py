from click.testing import CliRunner

import pyinfra

from pyinfra_cli.main import cli


def run_cli(*arguments):
    pyinfra.is_cli = True
    runner = CliRunner()
    result = runner.invoke(cli, arguments)
    pyinfra.is_cli = False
    return result
