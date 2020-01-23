# Using the CLI

``pyinfra`` is an extremely powerful tool for ad-hoc execution and management of remote servers.


## CLI arguments & options

As described in the [getting started page](./getting_started), ``pyinfra`` needs an **inventory** and some **operations**. These are used with the CLI as below:

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
pyinfra INVENTORY fact linux_distribution [users]...
pyinfra INVENTORY all-facts

# Debug (print) inventory hosts, groups and data
pyinfra INVENTORY debug-inventory
```

### Options

```sh
Options:
  -v                      Print std[out|err] from operations/facts.
  --user TEXT             SSH user to connect as.
  --port INTEGER          SSH port to connect to.
  --key PATH              Private key filename.
  --key-password TEXT     Privte key password.
  --password TEXT         SSH password.
  --sudo                  Whether to execute operations with sudo.
  --sudo-user TEXT        Which user to sudo when sudoing.
  --su-user TEXT          Which user to su to.
  --parallel INTEGER      Number of operations to run in parallel.
  --fail-percent INTEGER  % of hosts allowed to fail.
  --dry                   Don't execute operations on the target hosts.
  --limit TEXT            Restrict the target hosts by name and group name.
  --no-wait               Don't wait between operations for hosts to complete.
  --serial                Run operations in serial, host by host.
  --facts                 Print available facts list and exit.
  --operations            Print available operations list and exit.
  --version               Show the version and exit.
  --help                  Show this message and exit.
```


## Ad-hoc command execution

pyinfra can execute shell commands on remote hosts by using ``pyinfra exec``. For example:

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

For example here we ensure that `nginx` is installed on the remote servers:

```sh
pyinfra inventory.py apt.packages nginx sudo=true
```

#### Example: managing services with ad-hoc ``pyinfra`` commands

Now that nginx is installed on the box, we can use ``pyinfra`` to control the ``nginx`` service - here we ensure it's running and enabled to start on system boot:

```sh
pyinfra inventory.py init.service nginx running=true enabled=true
```

#### Additional debug info

For additional debug info, use one of these options:

+ `--debug` Print debug info.
+ `--debug-facts` Print facts after generating operations and exit.
+ `--debug-operations` Print operations after generating and exit.

#### Printing output in color

If you are developing a deploy script, and want to print the ouput in a different color,
you can use [click](https://click.palletsprojects.com) like this:

```sh
import click

from pyinfra import host

# To run: pyinfra @docker/ubuntu print_in_color.py

click.secho(host.fact.os_version, fg='yellow')
click.secho(host.fact.linux_name, fg='red')

```

