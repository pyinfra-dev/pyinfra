## pyinfra.modules.files


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
