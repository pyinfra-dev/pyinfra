## pyinfra.modules.server


##### pyinfra.modules.server.directory

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


##### pyinfra.modules.server.file

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


##### pyinfra.modules.server.init

Manage the state of init.d services.

```py
init(
    name,
    running=True,
    restarted=False
)
```


##### pyinfra.modules.server.script

[Not implemented] Run a script or file.

```py
script(
    code=None,
    file=None
)
```


##### pyinfra.modules.server.shell

[Not implemented] Run raw shell code.

```py
shell(
    code
)
```


##### pyinfra.modules.server.user

Manage Linux users & their ssh `authorized_keys`.

```py
user(
    name,
    present=True,
    home=None,
    shell=None,
    public_keys=None,
    delete_keys=False
)
```
