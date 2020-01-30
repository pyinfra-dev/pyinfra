'''
The windows module handles misc windows operations.
'''

from __future__ import unicode_literals

from pyinfra.api import operation

# Tip: Use 'Get-Command -Noun Service' to search for what commands are available or
# simply 'Get-Command' to see what you can do...)

# Tip: To see the windows help page about a command, use 'Get-Help'.
# Might have to run 'Update-Help' if you want to use arguments like '-Examples'.
# ex: 'Get-Help Stop-Service'
# ex: 'Get-Help Stop-Service -Examples'
# ex: 'Get-Help Stop-Service -Detailed'
# ex: 'Get-Help Stop-Service -Full'

# TODO: for processes
# Stop-Process <id>


@operation
def service(state, host, name, running=True):
    '''
    Stop/Start a Windows service.
    + name: name of the service to manage
    + running: whether the the service should be running

    Example:

    .. code:: python
        windows.service(
            {'Stop the spooler service'},
            'service',
            running=False,
        )
    '''

    # TODO: future options
    # Get-Service -Name <name> (ex: shows Running or Stopped)
    # Suspend-Service -Name <name>
    # Restart-Service -Name <name>

    # TODO: how to set this? (for now, override using cli)
    # shell_executable = 'ps'
    if running:
        yield 'Start-Service -Name {0}'.format(name)
    else:
        yield 'Stop-Service -Name {0}'.format(name)
