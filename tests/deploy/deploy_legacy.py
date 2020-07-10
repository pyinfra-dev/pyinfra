'''
This deploy uses legacy style (0.x) operation names and state/host arguments that
have been deprecated in v1. This will remain as a test to ensure backwards compatibility
until v2 is released.
'''

from pyinfra.api import deploy
from pyinfra.operations import server


@deploy('My nested deploy')
def my_nested_deploy(state, host):
    server.shell(
        state, host,  # positional state/host arguments = legacy
        {'First nested deploy operation'},  # set as first argument for name = legacy
        commands='echo first nested_deploy_op',
    )


@deploy('My deploy')
def my_deploy(state, host):
    my_nested_deploy(state, host)  # positional state/host arguments = legacy

    server.shell(
        state, host,  # positional state/host arguments = legacy
        name='Second deploy operation',
        commands='echo second_deploy_op',
    )


server.shell(
    {'First main operation'},  # set as first argument for name = legacy
    commands='echo first_main_op',
)

# Execute the @deploy function
my_deploy()
