# pyinfra
# File: pyinfra/example/config.py
# Desc: entirely optional config file for the CLI deploy
#       see: pyinfra/api/config.py for defaults

from pyinfra import hook


# These can be here or in deploy.py
TIMEOUT = 5
FAIL_PERCENT = 81


# Add hooks to be triggered throughout the deploy - separate to the operations
@hook.before_connect
def ensure_branch(data, state):
    # Run JS bundle build pre-deploy
    # local.shell('yarn run build')
    print('Before connect hook!')


@hook.after_deploy
def notify_people(data, state):
    print('After deploy hook!')
