---
orphan: true
---
# Using Secrets in pyinfra

## SOPS

[SOPS](https://github.com/getsops/sops) encrypts individual values in JSON/YAML files using age or PGP keys. pyinfra includes built-in support via `facts.sops` and `operations.sops`.

### Reading secrets with the SopsKey fact

Use `facts.sops.SopsKey` to read a single key from an encrypted file. When targeting `@local`, this runs on the local machine:

```py
# deploy.py
from pyinfra import host
from pyinfra.facts.sops import SopsKey

db_password = host.get_fact(SopsKey, secrets_file="secrets.enc.json", key="db_password")

postgresql.role(
    name="Create DB user",
    role="myapp",
    password=db_password,
)
```

The fact also works on remote hosts if `sops` is installed there and the key material is available.

### Writing secrets with sops.key

Use `operations.sops.key` to set or remove a key in an encrypted secrets file. The operation
is a no-op if the key already holds the expected value.

```py
import secrets
from pyinfra import host
from pyinfra.facts.sops import SopsKey
from pyinfra.operations import sops

# Bootstrap: generate once, keep forever
if host.get_fact(SopsKey, secrets_file="secrets.enc.json", key="db_password") is None:
    sops.key(
        name="Bootstrap DB password",
        secrets_file="secrets.enc.json",
        key="db_password",
        value=secrets.token_urlsafe(32),
    )

# Overwrite an existing key with a known value (e.g. from an external source)
sops.key(
    name="Store runner token",
    secrets_file="secrets.enc.json",
    key="gitlab_runner_token",
    value=runner_token,
)

# Remove a key (sets it to null)
sops.key(
    name="Remove deprecated key",
    secrets_file="secrets.enc.json",
    key="old_key",
    present=False,
)
```

### Passing environment variables to operations with INHERIT_ENV

Some tools (like `sops` itself, `glab`, cloud CLIs) read credentials from environment variables. Use `config.INHERIT_ENV` to forward specific variables from the local environment to all operations:

```py
# deploy.py
from pyinfra import config

# Forward SOPS age key and GitLab token from the caller's environment
config.INHERIT_ENV = ["SOPS_AGE_KEY_FILE", "GITLAB_TOKEN", "GITLAB_HOST"]
```

The priority order for environment variables is (lowest to highest):
1. `INHERIT_ENV` — inherited from the caller's `os.environ`
2. `config.ENV` — explicitly set in the deploy script
3. `_env` per-operation argument — overrides for a single operation

See also `config.ENV` in {doc}`../arguments`.

---

## Environment Variables

Read secrets directly from environment variables at inventory or group data load time:

```py
# group_data/all.py
import os

db_password = os.environ["DB_PASSWORD"]
```

---

## privy

Encrypting individual values can be done with [privy](https://pypi.org/project/privy/). Prompt interactively for the decryption password:

```py
# group_data/all.py
from getpass import getpass

import privy

def get_secret(encrypted_secret):
    password = getpass('Please provide the secret password: ')
    return privy.peek(encrypted_secret, password)

my_secret = get_secret('encrypted-secret-value')
```

Or read the password from an environment variable:

```py
import os

import privy

def get_secret(encrypted_secret):
    password = os.environ['TOP_SECRET_PASSWORD']
    return privy.peek(encrypted_secret, password)
```

