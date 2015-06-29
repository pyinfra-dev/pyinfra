## pyinfra.modules.files


##### function: directory

Manage the state of directories.

```py
directory(
    name,
    present=True,
    user=None,
    group=None,
    mode=None,
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
    mode=None,
    touch=False
)
```


##### function: put

Copy a local file to the remote system.

```py
put(
    local_file,
    remote_file
)
```


##### function: template

Generate a template and write it to the remote system.

```py
template(
    template_file,
    remote_file,
    **data
)
```
