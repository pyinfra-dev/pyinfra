import click

from pyinfra_cli.__main__ import cli

click.echo(click.style("Warning: running alpha pyinfra binary build", "yellow"), err=True)
cli()
