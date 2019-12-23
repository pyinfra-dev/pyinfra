# Connectors

Connectors enable pyinfra to integrate with other tools out of the box. Connectors can do two things:

+ Generate inventory hosts and data (`@vagrant`)
+ Modify how commands are executed (`@local`)
+ Both of the above (`@docker`)

If you're interested in building a connector, check out [the existing code](https://github.com/Fizzadar/pyinfra/tree/master/pyinfra/api/connectors). Each connector is described below along with usage examples:

## `@local`

The `@local` connector executes changes on the local machine using subprocesses.

```sh
pyinfra @local deploy.py
```

## `@vagrant`

The `@vagrant` connector reads the current Vagrant status and generates an inventory for any running VMs.

```sh
# Run on all hosts
pyinfra @vagrant deploy.py

# Run on a specific VM
pyinfra @vagrant/my-vm-name deploy.py

# Run on multiple named VMs
pyinfra @vagrant/my-vm-name,@vagrant/another-vm-name deploy.py
```

## `@docker`

**Note**: this connector is a work in progress! It works but may leave containers leftover, and some operations may fail.

The `@docker` connector allows you to build Docker containers using pyinfra.

```sh
# A Docker base image must be provided
pyinfra @docker/alpine:3.8 deploy.py

# pyinfra can build multiple Docker images in parallel
pyinfra @docker/alpine:3.8,@docker/ubuntu:bionic deploy.py
```

## `@ansible`

**Note**: this connector is a work in progress! While it parses the list of hosts OK, it doesn't handle nested groups properly yet.

The `@ansible` connector can be used to parse Ansible inventory files.

```sh
# Load an Ansible inventory relative to the current directory
pyinfra @ansible/path/to/inventory

# Load using an absolute path
pyinfra @ansible//absolute/path/to/inventory
```
