# Connectors

Connectors are used by pyinfra to integrate with other tools. Connectors are specified as inventory hosts and can alter the inventory creation and/or execution.

## `@docker`

The `@docker` connector allows you to build Docker containers using pyinfra.

```sh
# A Docker base image must be provided
pyinfra @docker/alpine:3.8 deploy.py

# pyinfra can build multiple Docker images in parallel
pyinfra @docker/alpine:3.8,ubuntu:bionic deploy.py
```

## `@local`

The `@local` connector executes changes on the local machine using subprocess.

```sh
pyinfra @local deploy.py
```

## `@vagrant`

The `@vagrant` connector reads the current Vagrant status and generates an inventory for anny running VMs.

```sh
# Run on all hosts
pyinfra @vagrant deploy.py

# Run on a specific VM
pyinfra @vagrant/my-vm-name deploy.py

# Run on multiple named VMs
pyinfra @vagrant/my-vm-name,another-vm-name deploy.py
```
