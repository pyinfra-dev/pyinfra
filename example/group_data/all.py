# pyinfra
# File: example/group_vars/all.py
# Desc: config/variables which apply to all hosts, must be snake_case

# Required
ssh_user = 'vagrant'
# Without a ~ or / at the start, this is relative to the deploy(.py) file
ssh_key = 'files/insecure_private_key'

# Anything else
env_dir = '/opt/env'
app_dir = '/opt/pyinfra'
