"""
The windows module handles misc windows operations.
"""

from pyinfra.api import operation

# Tip: Use 'Get-Command -Noun Service' to search for what commands are available or
# simply 'Get-Command' to see what you can do...)

# Tip: To see the windows help page about a command, use 'Get-Help'.
# Might have to run 'Update-Help' if you want to use arguments like '-Examples'.
# ex: 'Get-Help Stop-Service'
# ex: 'Get-Help Stop-Service -Examples'
# ex: 'Get-Help Stop-Service -Detailed'
# ex: 'Get-Help Stop-Service -Full'

# FUTURE: add ability to stop processes (ex: "Stop-Process <id>")


@operation(is_idempotent=False)
def service(service, running=True, restart=False, suspend=False):
    """
    Stop/Start a Windows service.

    + service: name of the service to manage
    + running: whether the the service should be running or stopped
    + restart: whether the the service should be restarted
    + suspend: whether the the service should be suspended

    **Example:**

    .. code:: python

        windows.service(
            name="Stop the spooler service",
            service="service",
            running=False,
        )
    """

    if suspend or not running:
        if suspend:
            yield "Suspend-Service -Name {0}".format(service)
        else:
            yield "Stop-Service -Name {0}".format(service)
    else:
        if restart:
            yield "Restart-Service -Name {0}".format(service)
        else:
            if running:
                yield "Start-Service -Name {0}".format(service)


@operation(is_idempotent=False)
def reboot():
    """
    Restart the server.
    """
    yield "Restart-Computer -Force"
