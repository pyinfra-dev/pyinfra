import click

from pyinfra import host
from pyinfra.facts.server import LinuxName, OsVersion

# To run: pyinfra @docker/ubuntu print_in_color.py

click.secho(host.get_fact(OsVersion), fg='yellow')
click.secho(host.get_fact(LinuxName), fg='red')
