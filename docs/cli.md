# Using the CLI

The pyinfra is an extremely powerful tool for ad-hoc execution and management of remote servers.

## Command Execution

pyinfra can execute shell commands on remote hosts by using ``pyinfra exec``. For example:

```sh
pyinfra inventory.py exec -- my_command_goes_here --some-argument
```

Note:
    Anything on the right hand side of the ``--`` will be passed into the target

### Debugging distributed services using pyinfra

One of pyinfra's top design features is its ability to return remote command output in realtime. This can be used to debug N remote services, and is perfect for debugging distributed services.

For example - a large Elasticsearch cluster. It can be useful to stream the log of every instance in parallel, which can be achieved easily like so:

```sh
pyinfra inventory.py exec --sudo -- tail -f /var/log/elasticsearch/elasticsearch.log
```

## Operations

In addition to executing simple commands, pyinfra can execute any of it's builtin operations on remote hosts direct via the CLI. For example here we ensure that `htop` is installed on the remote servers:

```sh
pyinfra inventory.py apt.packages htop sudo=true
```
