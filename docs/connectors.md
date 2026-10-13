# Connectors

Connectors enable pyinfra to integrate with other tools out of the box. Connectors can do one of three things:

- Implement how commands are executed (`@ssh`, `@local`)
- Generate inventory hosts and data (`@terraform` and `@vagrant`)
- Both of the above (`@docker`, `@podman`, and other container connectors)

Each connector page is listed below and contains examples as well as a list of available data that can be used to configure the connector.

**Want a new connector?** Check out [the writing connectors guide](api/connectors.md).

### Popular connectors

- [`@ssh`](connectors/ssh.md) — Connect to any SSH server.
- [`@docker`](connectors/docker.md) — Create or modify Docker containers.
- [`@terraform`](connectors/terraform.md) — Get SSH targets from Terraform output.
- [`@local`](connectors/local.md) — Connect to the local machine running pyinfra.
