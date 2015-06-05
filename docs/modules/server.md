## pyinfra.modules.server

The server module attempts to take care of os-level state. While it is primarily targetted towards
Linux we try to stick to Unix as much as possible for greater compatability with BSD/etc.

##### function: directory

Manage the state of directories.

```py
directory(
    name,
    present=True,
    user=None,
    group=None,
    permissions=None,
    recursive=False
)
```


##### function: file

Manage the state of files.

```py
file(
    name,
    present=True,
    user=None,
    group=None,
    permissions=None,
    touch=False
)
```


##### function: init

Manage the state of init.d services.

```py
init(
    name,
    running=True,
    restarted=False,
    reloaded=False
)
```


##### function: script

Upload and execute a local script on the remote host.

```py
script(
    filename
)
```


##### function: shell

Run raw shell code.

```py
shell(
    code
)
```


##### function: user

Manage Linux users & their ssh `authorized_keys`.

```py
user(
    name,
    present=True,
    home=None,
    shell=None,
    public_keys=None, # list of public keys to attach to this user
    delete_keys=False # deletes existing keys when `public_keys` specified
)
```
