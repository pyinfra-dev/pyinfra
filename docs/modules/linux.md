# Linux

#### linux directory

Manage the state of directories.

```py
linux.directory(
    name,
    present=True,
    user=None,
    group=None,
    permissions=None,
    recursive=False
)
```

#### linux file

Manage the state of files.

```py
linux.file(
    name,
    present=True,
    user=None,
    group=None,
    permissions=None,
    touch=False
)
```

#### linux init

Manage the state of init.d services.

```py
linux.init(
    name,
    running=True,
    restarted=False
)
```

#### linux user

Manage Linux users & their ssh `authorized_keys`.

```py
linux.user(
    name,
    present=True,
    home=None,
    shell=None,
    public_keys=None,
    delete_keys=False
)
```
