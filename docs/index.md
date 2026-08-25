# pyinfra Documentation

Welcome to the pyinfra v3 documentation. If you're new to pyinfra you should start with [Getting Started](getting-started.md).

## Using pyinfra

- [**Getting Started**](getting-started.md) — Start here! The quickest way to learn the basics of pyinfra and get started.
- [**Using Operations**](using-operations.md) — The guide to writing reusable, committable operations in Python files.
- [**Inventory & Data**](inventory-data.md) — Use groups, host, and group data to control and configure operations for any environment.
- [**Using the CLI**](cli.md) — The pyinfra CLI is extremely powerful for ad hoc command execution and management.
- [**Debugging Deploys**](debugging.md) — Inspect inventory, facts and operations, and add focused diagnostic logging.
- [**FAQ**](faq.md) — Quick answers to the most commonly asked questions for using pyinfra.

## Deploy Reference

- [**Operations**](operations.md) — A list of all available operations and their arguments, e.g. `apt.packages`.
- [**Facts**](facts.md) — A list of all facts pyinfra can gather from hosts, e.g. `server.Hostname`.
- [**Connectors**](connectors.md) — A list of connectors to target different hosts such as `@docker`, `@local` and `@terraform`.
- [**Arguments**](arguments.md) — Arguments available in all operations & facts such as `_sudo`, `_serial` and `_env`

## How pyinfra Works

- [**Deploy Process**](deploy-process.md) — Discover how pyinfra orders, diffs and executes operations against target hosts.
- [**Writing Deploys**](api/deploys.md) — How to package, redistribute and share pyinfra deploys as Python packages.
- [**Writing Connectors**](api/connectors.md) — How to write your own connectors for pyinfra.
- [**Writing Operations**](api/operations.md) — How to write your own operations for pyinfra.
- [**Writing Facts**](api/facts.md) — How to write your own facts for pyinfra.
- [**Using the API**](api/index.md) — How to use the pyinfra API.
