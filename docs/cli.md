# Using the CLI

``pyinfra`` is an extremely powerful tool for ad-hoc execution and management of remote servers.


## CLI arguments & options

As described in the [getting started page](./getting_started), `pyinfra` needs an **inventory** and some **operations**. These are used with the CLI as below:

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

By default `pyinfra` only prints high level information (this host connected, this operation started), this can be increased as follows:

+ `-v`: print out facts collected as well as noop information (package X already installed)
+ `-vv`: as above plus print shell input to the remote host
+ `-vvv` as above plus print shell output from the remote host


## Inventory

When using ``pyinfra`` inventory can be provided direct via the command line or [defined in a file](./deploys.html#inventory). Both support the full range of [connectors](./connectors) and multiple hosts. Some CLI examples:

```sh
pyinfra inventory.py ...  # load the inventory targets from this file
pyinfra my-server.net,my-other-server.net ...  # execute via SSH on the two servers listed
pyinfra @local ...  # execute on the local machine via subprocess
pyinfra my-server.net,@local ...  # execute via local subprocess and a server over SSH
pyinfra @docker/centos:8 ...  # execute against a Docker container
```

### Limit

It is possible to limit the inventory at execution time using the `--limit` argument. Multiple `--limit`s can be provided. The value must either match a specific host by name or via glob style pattern, eg:

```sh
pyinfra @local,my-server.net --limit @local ...  # only execute against @local
pyinfra @local,my-server.net --limit *.net ...  # only execute against my-server.net
pyinfra inventory.py --limit one-host.net --limit another-host.net ...  # multiple limit inventory file
```


## Ad-hoc command execution

``pyinfra`` can execute shell commands on remote hosts by using `pyinfra exec`. For example:

```sh
pyinfra inventory.py exec -- my_command_goes_here --some-argument
```

Note:
    Anything on the right hand side of the ``--`` will be passed into the target

#### Example: debugging distributed services using ``pyinfra``

One of ``pyinfra``'s top design features is its ability to return remote command output in real-time. This can be used to debug N remote services, and is perfect for debugging distributed services.

For example - a large Elasticsearch cluster. It can be useful to stream the log of every instance in parallel, which can be achieved easily like so:

```sh
pyinfra inventory.py exec --sudo -- tail -f /var/log/elasticsearch/elasticsearch.log
```

### Executing ad-hoc operations

In addition to executing simple commands, ``pyinfra`` can execute any of it's builtin operations on remote hosts direct via the CLI.

#### Example: managing packages with ad-hoc ``pyinfra`` commands

For example, here we ensure that `nginx` is installed on the remote servers:

```sh
# Ubuntu example
pyinfra inventory.py apt.packages nginx sudo=true update=true

# Centos example
pyinfra inventory2.py yum.packages nginx sudo=true
```

#### Example: managing services with ad-hoc ``pyinfra`` commands

Now that nginx is installed on the box, we can use ``pyinfra`` to control the ``nginx`` service - here we ensure it's running and enabled to start on system boot:

```sh
pyinfra inventory.py init.service nginx running=true enabled=true
```

#### Example: rebooting with ad-hoc ``pyinfra`` commands

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
env _PYINFRA_COMPLETE=source pyinfra > pyinfra-complete.sh
env _PYINFRA_COMPLETE=source_zsh pyinfra > pyinfra-complete.zsh
```
