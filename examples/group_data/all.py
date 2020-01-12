# pyinfra
# File: example/group_data/all.py
# Desc: config/variables which apply to all hosts, must be snake_case

# Required
ssh_user = 'vagrant'
ssh_key = 'files/insecure_private_key'

# Anything else
env_dir = '/opt/env'
app_dir = '/opt/pyinfra'
app_branch = 'develop'
