# Ansible Module Execution

This example runs a real Ansible module (`ansible.builtin.ping`) through pyinfra.

The module source lives at `examples/ansible_modules/ping.py` (downloaded from ansible/ansible).

## CLI Usage

```sh
pyinfra -y -v @local ansible.module examples/ansible_modules/ping.py data=pyinfra
```

## Deploy Usage

```python
from pyinfra.operations import ansible

ansible.module(
    name="Run ansible.builtin.ping",
    src="examples/ansible_modules/ping.py",
    kwargs={"data": "pyinfra"},
)
```
