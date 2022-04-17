from os import chdir, getcwd

from click.testing import CliRunner

import pyinfra
from pyinfra_cli.main import cli


def run_cli(*arguments):
    cwd = getcwd()
    pyinfra.is_cli = True
    runner = CliRunner()
    result = runner.invoke(cli, arguments)
    pyinfra.is_cli = False
    chdir(cwd)
    return result
