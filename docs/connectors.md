# Connectors

Connectors enable ``pyinfra`` to integrate with other tools out of the box. Connectors can do one of three things:

+ Generate inventory hosts and data (`@vagrant` and `@mech`)
+ Modify how commands are executed (`@ssh`, `@local`)
+ Both of the above (`@docker`)

Each connector is described below along with usage examples.

**Want a new connector?** If interested in building a connector, check out [the existing code](https://github.com/Fizzadar/pyinfra/tree/master/pyinfra/api/connectors). Be sure to add tests and documentation.

## `@ssh`

This is the default connector and all targets default to this meaning you do not need to specify it - ie the following two commands are identical:

```sh
pyinfra my-host.net ...
pyinfra @ssh/my-host.net ...
```

## `@local`

The `@local` connector executes changes on the local machine using subprocesses.

```sh
pyinfra @local ...
```

## `@docker`

**Note**: this connector is in beta!

The `@docker` connector allows you to build Docker containers using pyinfra.

```sh
# A Docker base image must be provided
pyinfra @docker/alpine:3.8 ...

# pyinfra can run on multiple Docker images in parallel
pyinfra @docker/alpine:3.8,@docker/ubuntu:bionic ...
```

## `@dockerssh`

**Note**: this connector is in beta!

The `@dockerssh` connector allows you to run commands on Docker containers on a remote machine.

```sh
# A Docker base image must be provided
pyinfra @dockerssh/remotehost:alpine:3.8 ...

# pyinfra can run on multiple Docker images in parallel
pyinfra @dockerssh/remotehost:alpine:3.8,@dockerssh/remotehost:ubuntu:bionic ...
```

## `@vagrant`

The `@vagrant` connector reads the current Vagrant status and generates an inventory for any running VMs.

```sh
# Run on all hosts
pyinfra @vagrant ...

# Run on a specific VM
pyinfra @vagrant/my-vm-name ...

# Run on multiple named VMs
pyinfra @vagrant/my-vm-name,@vagrant/another-vm-name ...
```

## `@mech`

The `@mech` connector reads the current mech status and generates an inventory for any running VMs.

```sh
# Run on all hosts
pyinfra @mech ...

# Run on a specific VM
pyinfra @mech/my-vm-name ...

# Run on multiple named VMs
pyinfra @mech/my-vm-name,@mech/another-vm-name ...
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

## `@winrm`

**Note**: this connector is experimental and a work in progress! Some Windows facts and Windows operations work but this is to be considered experimental. For now, only `winrm-username` and `winrm-password` is being used. There are other methods for authentication, but they have not yet been added/experimented with.

The `@winrm` connector can be used to communicate with Windows instances that have WinRM enabled.

Examples using `@winrm`:

```sh
# get the windows_home fact
pyinfra @winrm/192.168.3.232 --winrm-username vagrant --winrm-password vagrant --winrm-port 5985 -vv --debug fact windows_home
# create a directory
pyinfra @winrm/192.168.3.232 --winrm-username vagrant --winrm-password vagrant --winrm-port 5985 windows_files.windows_directory 'c:\temp'
# Run a powershell command ('ps' is the default shell-executable for the winrm connector)
pyinfra @winrm/192.168.3.232 --winrm-username vagrant --winrm-password vagrant --winrm-port 5985 exec -- write-host hello
# Run a command using the command prompt:
pyinfra @winrm/192.168.3.232 --winrm-username vagrant --winrm-password vagrant --winrm-port 5985 --shell-executable cmd exec -- date /T
```
