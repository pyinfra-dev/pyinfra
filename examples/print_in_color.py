import click

from pyinfra import host

print(click.style(host.fact.os_version, 'yellow'))
