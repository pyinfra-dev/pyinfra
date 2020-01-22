import click

from pyinfra import host

# To run: pyinfra @docker/ubuntu print_in_color.py

click.secho(host.fact.os_version, fg='yellow')
click.secho(host.fact.linux_name, fg='red')
