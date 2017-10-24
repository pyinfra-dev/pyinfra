# pyinfra
# File: pyinfra/example/config.py
# Desc: entirely optional config file for the CLI deploy
#       see: pyinfra/api/config.py for defaults

from pyinfra import hook, local


# These can be here or in deploy.py
TIMEOUT = 5
FAIL_PERCENT = 81


# Add hooks to be triggered throughout the deploy - separate to the operations
@hook.before_connect
def ensure_branch(data, state):
    # Check something local is correct, etc
    branch = local.shell('git rev-parse --abbrev-ref HEAD')
    app_branch = data.app_branch

    if branch != app_branch:
        # Raise hook.Error for pyinfra to handle
        raise hook.Error('We\'re on the wrong branch (want {0}, got {1})!'.format(
            app_branch, branch,
        ))


@hook.after_deploy
def notify_people(data, state):
    print('After deploy hook!')
