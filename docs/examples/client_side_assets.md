# Client Side Assets

Often projects need to pre-compile assets at deploy time to be uploaded to the remote host.
This can be achieved using hooks and the ``pyinfra.local`` module.

In the following example the branch is first checked (to ensure deploy branch/local branch
match) and the client assets are then built before pyinfra connects to any hosts:

```py
# config.py

from pyinfra import hook, local

@hook.before_connect
def check_branch(data, state):
    # Check local branch matches the deploy branch
    branch = local.shell('git rev-parse --abbrev-ref HEAD')
    app_branch = data.app_branch

    if branch != app_branch:
        # Raise hook.Error for pyinfra to handle
        raise hook.Error('We\'re on the wrong branch (want {0}, got {1})!'.format(
            branch, app_branch,
        ))

@hook.before_connect
def build_assets(data, state):
    # Prep for clientside build
    local.shell('npm prune')
    local.shell('npm install')

    # Build the assets (using webpack in this case)
    local.shell('webpack --progress')
```

Simply place this ``config.py`` alongside your deploys and pyinfra will pick it up.
