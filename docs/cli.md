# Using the CLI

pyinfra is an extremely powerful tool for ad-hoc execution and management of remote servers.


## CLI arguments & options

As described in the [getting started page](./getting-started), pyinfra needs an **inventory** and some **operations**. These are used with the CLI as below:

```sh
Usage: pyinfra [OPTIONS] INVENTORY OPERATIONS...

# INVENTORY

+ a file (inventory.py)
+ hostname (host.net)
+ Comma separated hostnames: host-1.net,host-2.net,@local

# OPERATIONS

# Run one or more deploys against the inventory
pyinfra INVENTORY deploy_web.py [deploy_db.py]...

# Run a single operation against the inventory
pyinfra INVENTORY server.user pyinfra home=/home/pyinfra

# Execute an arbitrary command on the inventory
pyinfra INVENTORY exec -- echo "hello world"

# Run one or more facts on the inventory
pyinfra INVENTORY fact server.LinuxName [server.Users]...
pyinfra INVENTORY fact files.File path=/path/to/file...

# Debug (print) inventory hosts, groups and data
pyinfra INVENTORY debug-inventory
```

### Verbosity

By default pyinfra only prints high level information (this host connected, this operation started), this can be increased as follows:

+ `-v`: print out facts collected as well as noop information (package X already installed)
+ `-vv`: as above plus print shell input to the remote host
+ `-vvv` as above plus print shell output from the remote host

### Retry Options

pyinfra supports automatic retry of failed operations via CLI options:

+ `--retry N`: Retry failed operations up to N times (default: 0)
+ `--retry-delay N`: Wait N seconds between retry attempts (default: 5)

```sh
# Retry failed operations up to 3 times with default 5 second delay
pyinfra inventory.py deploy.py --retry 3

# Retry with custom delay
pyinfra inventory.py deploy.py --retry 2 --retry-delay 10
```


## Inventory

When using pyinfra inventory can be provided directly via the command line or [defined in a file](./inventory-data). Both support the full range of [connectors](./connectors) and multiple hosts. Some CLI examples:

```sh
# Load inventory hosts from a file
pyinfra inventory.py ...

# Execute via SSH against two servers
pyinfra my-server.net,my-other-server.net ...

# Execute on the local machine via subprocess
pyinfra @local ...

# Execute via local subprocess and a server over SSH
pyinfra my-server.net,@local ...

# Execute against a Docker container
pyinfra @docker/fedora:43 ...
```

### Limit

It is possible to limit the inventory at execution time using the `--limit` argument. Multiple `--limit`s can be provided. The value must either match a specific host by name or via glob style pattern, eg:

```sh
# Only execute against @local
pyinfra inventory.py deploy.py --limit @local

# Only execute against hosts in the `app_servers` group
pyinfra inventory.py deploy.py --limit app_servers

# Only execute against hosts with names matching db*
pyinfra inventory.py deploy.py --limit "db*"

# Combine multiple limits
pyinfra inventory.py deploy.py --limit app_servers --limit db-1.net
```


## Ad-hoc command execution

pyinfra can execute shell commands on remote hosts by using `pyinfra exec`. For example:

```sh
pyinfra inventory.py exec -- my_command_goes_here --some-argument
```

Note:
    Anything on the right hand side of the ``--`` will be passed into the target

### Example: debugging distributed services using pyinfra

One of pyinfra's top design features is its ability to return remote command output in real-time. This can be used to debug N remote services, and is perfect for debugging distributed services.

For example - a large Elasticsearch cluster. It can be useful to stream the log of every instance in parallel, which can be achieved easily like so:

```sh
pyinfra inventory.py exec --sudo -- tail -f /var/log/elasticsearch/elasticsearch.log
```

## Executing ad-hoc operations

In addition to executing simple commands, pyinfra can execute any of it's builtin operations on remote hosts direct via the CLI.

### Example: managing packages with ad-hoc pyinfra commands

For example, here we ensure that `nginx` is installed on the remote servers:

```sh
# Ubuntu example
pyinfra inventory.py apt.packages nginx update=true _sudo=true

# Fedora example
pyinfra inventory2.py yum.packages nginx _sudo=true
```

### Example: managing services with ad-hoc pyinfra commands

Now that nginx is installed on the box, we can use pyinfra to control the ``nginx`` service - here we ensure it's running and enabled to start on system boot:

```sh
pyinfra inventory.py init.service nginx running=true enabled=true
```

#### Example: rebooting with ad-hoc pyinfra commands

We can reboot instances a couple of ways using adhoc commands (assuming *sudo* is enabled in inventory.py):

```sh
# using server.reboot()
pyinfra inventory.py server.reboot reboot_timeout=0 delay=0

# using exec
pyinfra inventory.py exec -- reboot
```

#### Additional debug info

For additional debug info, use one of these options:

+ `--debug` Print debug info.
+ `--debug-facts` Print facts after generating operations and exit.
+ `--debug-operations` Print operations after generating and exit.


## Shell Autocompletion

Add the following to your `~/.bash_profile` or `~/.profile` files:

+ **bash** `source scripts/pyinfra-complete.sh`.
+ **zsh** `source scripts/pyinfra-complete.zsh`.

These files were generated using these commands:

```
env _PYINFRA_COMPLETE=bash_source pyinfra > pyinfra-complete.sh
env _PYINFRA_COMPLETE=zsh_source pyinfra > pyinfra-complete.zsh
```
