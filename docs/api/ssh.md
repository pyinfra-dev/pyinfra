## pyinfra.api.ssh


##### pyinfra.api.ssh.connect_all

Connect to all the configured servers.

```py
connect_all()
```


##### pyinfra.api.ssh.run_all_command

Runs a single command on all hosts in parallel, used for collecting facts.

```py
run_all_command()
```


##### pyinfra.api.ssh.run_op

Runs a single operation on a remote server.

```py
run_op(
    hostname,
    op_hash,
    print_output=False
)
```


##### pyinfra.api.ssh.run_ops

Runs all operations across all servers in a configurable manner.

```py
run_ops(
    serial=False,
    nowait=False,
    print_output=False
)
```
