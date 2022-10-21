# Using Secrets in pyinfra

Encrypting sensitive information can be achieved using Python packages such as [privy](https://pypi.org/project/privy/).

```py
# group_data/all.py

from getpass import getpass

import privy

def get_secret(encrypted_secret):
    password = getpass('Please provide the secret password: ')
    return privy.peek(encrypted_secret, password)

my_secret = get_secret('encrypted-secret-value')
```

An alternative might use an environment variable for the password:

```py
import os

import privy

def get_secret(encrypted_secret):
    password = os.environ['TOP_SECRET_PASSWORD']
    return privy.peek(encrypted_secret, password)
```
