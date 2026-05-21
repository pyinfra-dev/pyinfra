# Chain Connector

The `@chain` connector enables arbitrary nesting of connectors using the `/@` delimiter
syntax. It allows you to target hosts that are only reachable through a chain of
intermediate connectors — for example, a Docker container running on a remote SSH host.

## Syntax

```
pyinfra @outer/arg/@inner/arg[/@deeper/arg...] <operations>
```

- The left-most connector is the **outermost** (it owns the real network connection).
- The right-most connector is the **innermost** (closest to the target).
- The `/@` delimiter separates connectors in the chain.

## Examples

```shell
# Execute in a Docker container on a remote host via SSH
pyinfra @ssh/mydoodba/@docker/myodoodev16-odoo-1 files.put src/ /opt/odoo/

# Chroot into a build rootfs on a remote host via SSH
pyinfra @ssh/build-server/@chroot/rootfs server.shell "ls /"

# Three-level chain: local → SSH → Docker
pyinfra @ssh/jumpbox/@docker/mycontainer server.shell "whoami"
```

## How it works

1. **Parsing**: `/@` in an inventory name is detected and routed to `ChainedConnector`.
2. **Data collection**: Each connector's `make_names_data` is called to collect inventory data.
3. **Connection**: Only the outermost connector is connected (e.g. SSH socket).
4. **Command execution**: Commands are wrapped innermost-to-outermost into a single shell
   string, then executed via the outer connector.
5. **File transfer**: Files are pipelined through temp paths at each layer — uploaded to the
   outer host, copied inward layer by layer, and cleaned up after.

## Requirements for inner connectors

A connector that can be used as an **inner** layer in a chain must implement:

- `wrap_exec_command(command, container_id)` — wraps a command to run inside the target
- `wrap_copy_into(src, dest, container_id)` — copies a file from the parent into the target
- `wrap_copy_out(src, dest, container_id)` — copies a file from the target to the parent

The `container_id` parameter is the runtime identifier returned by the connector's
`get_runtime_id()` method. By default, `get_runtime_id()` reads the data key specified by
the `runtime_id_field` class attribute.

Connectors that only work as an **outer** layer (e.g. SSH, which depends on paramiko
sockets) raise `NotImplementedError` when used as an inner connector.

## Limitations

- Two connectors of the same type cannot appear in the same chain (they share conflicting
  data keys in `host.data`). Use SSH `ProxyJump` in `~/.ssh/config` for ssh-over-ssh.
- The chain syntax cannot appear inside a multi-host comma-separated list.
