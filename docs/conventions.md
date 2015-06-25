# pyinfra conventions

## CLI Usage

Deploy folders should look something like this:

+ `deploy.py` or `*.py` - deploy scripts
+ `inventories/*.py` or `inventory.py` - inventory script(s)
+ `group_vars/`
    * `all.py` - group variable script all hosts inherit
    * `<environment>.py` - variable scripts for specific inventory groups
+ `templates/` - Jinja2 templates for the deploy
+ `files/` - static files for the deploy

### Inventory scripts

```py
# Group config in ALL_CAPS
GROUP = ['myhost']
```

### Deploy scripts

```py
# Imports...

# Config in ALL_CAPS
SUDO=True

# Module calls
server.shell('echo "Hello World."')
```

### Variable scripts

```py
# Variables in snake_case
my_var = '/opt/env'
```


## API Usage

Coming soon.
