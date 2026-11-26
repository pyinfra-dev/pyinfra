# Connectors

Connectors enable pyinfra to integrate with other tools out of the box. Connectors can do one of three things:

- Implement how commands are executed (`@ssh`, `@local`)
- Generate inventory hosts and data (`@terraform` and `@vagrant`)
- Both of the above (`@docker`, `@podman`, and other container connectors)

All built-in connector pages are listed below. Each page contains examples and the data used to configure the connector.

**Want a new connector?** Check out [the writing connectors guide](api/connectors.md).

### Available connectors

- [`@chroot`](connectors/chroot.md): Execute operations within another root.
- [`@docker`](connectors/docker.md): Create or modify Docker containers.
- [`@dockerssh`](connectors/dockerssh.md): Run commands in Docker containers on a remote machine.
- [`@fake`](connectors/fake.md): Simulate command execution and file transfers locally.
- [`@incus`](connectors/incus.md): Target running containers and agent-enabled VMs on local or remote Incus daemons.
- [`@lxc`](connectors/lxc.md): Use the Incus connector implementation with the `lxc` command.
- [`@local`](connectors/local.md): Connect to the local machine running pyinfra.
- [`@podman`](connectors/podman.md): Create or modify Podman containers.
- [`@podmanssh`](connectors/podmanssh.md): Run commands in Podman containers on a remote machine over SSH.
- [`@ssh`](connectors/ssh.md): Connect to any SSH server.
- [`@terraform`](connectors/terraform.md): Get SSH targets from Terraform output.
- [`@vagrant`](connectors/vagrant.md): Generate inventory from running Vagrant VMs.
