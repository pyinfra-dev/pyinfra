from pyinfra import local
from pyinfra.modules import init, python


def on_pyinfra_success(state, host, op_hash):
    print('Success on {0} for OP: {1}!'.format(host.name, op_hash))


def on_pyinfra_error(state, host, op_hash):
    print('Error on {0} for OP: {1}!'.format(host.name, op_hash))


# Manage init systems
init.service(
    {'Ensure cron service with error callback'},
    'cron',
    running=True,
    sudo=True,
    ignore_errors=True,
    on_success=on_pyinfra_success,
    on_error=on_pyinfra_error,
)


# Execute Python locally, mid-deploy
def some_python(state, host, *args, **kwargs):
    print('connecting host name: {0}, actual: {1}'.format(host.name, host.fact.hostname))
    local.shell('echo "local stuff!"')


python.call(
    {'Execute some_python function'},
    some_python,
    'arg1', 'arg2',
    kwarg='hello world',
)
