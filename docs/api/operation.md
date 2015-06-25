## pyinfra.api.operation

Operations are the core of pyinfra. These wrappers mean that when you call an operation
in a deploy script, what actually happens is we diff the remote server and build a list
of commands to alter the diff to the specified arguments. This is then saved to be run
later by pyinfra's __main__.

##### function: add_op

Prepare & add an operation to pyinfra.state by executing it on all hosts.

```py
add_op(
    op_func,
    *args,
    **kwargs
)
```


##### function: operation

Takes a simple module function and turn it into the internal operation representation
consists of a list of commands + options (sudo, user, env).

```py
operation(
    func
)
```


##### function: operation_env

Pre-wraps an operation with kwarg environment variables

```py
operation_env()
```
