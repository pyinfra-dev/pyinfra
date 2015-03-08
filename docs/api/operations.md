## pyinfra.api.operations


##### pyinfra.api.operations.run_op

Runs a single operation on a remote server.

```py
run_op(
    hostname,
    op_hash,
    print_output=False,
    *None,
    **None
)
```


##### pyinfra.api.operations.run_ops

Runs all operations across all servers in a configurable manner.

```py
run_ops(
    serial=False,
    nowait=False,
    print_output=False,
    *None,
    **None
)
```
