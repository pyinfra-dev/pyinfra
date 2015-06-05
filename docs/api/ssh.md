## pyinfra.api.ssh


##### function: connect_all

Connect to all the configured servers in parallel.

```py
connect_all()
```


##### function: put_file

Upload/sync local/remote directories & files to the specified host.

```py
put_file(
    hostname,
    file_io,
    remote_file,
    sudo=False,
    sudo_user=None,
    print_output=False,
    print_prefix=''
)
```


##### function: run_shell_command

Execute a command on the specified host.

```py
run_shell_command(
    hostname,
    command,
    sudo=False,
    sudo_user=None,
    env=None,
    print_output=False,
    print_prefix=''
)
```
