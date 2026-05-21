# Connectors

Connectors enable pyinfra to integrate with other tools out of the box. Connectors can do one of three things:

- Implement how commands are executed (`@ssh`, `@local`)
- Generate inventory hosts and data (`@terraform` and `@vagrant`)
- Both of the above (`@docker`, `@podman`, and other container connectors)

All built-in connector pages are listed below. Each page contains examples and the data used to configure the connector.

**Want a new connector?** Check out [the writing connectors guide](api/connectors.md).

### Available connectors

- [`@chain`](connectors/chain.md): Chain multiple connectors to reach nested targets.
- [`@chroot`](connectors/chroot.md): Execute operations within another root.
