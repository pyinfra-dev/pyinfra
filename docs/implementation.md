# Implementation

The "lowest" level on which most people deploy a Linux box is via the shell, which is what pyinfra targets. pyinfra dynamically builds SSH command sets by reading the desired state from a config file and checking the server for current state when needed. It essentially does a diff between the config and the live state, and generates commands to change the state to that of the config.

When a deploy is run, the following happens:

+ The config file is loaded and assigned to `pyinfra.config`
+ SSH connections are opened to each server
+ For each target server, the deploy script is executed with `pyinfra._current_server` set
    - The calls to each module populate `pyinfra._commands` with commands to run on each server
    - Any calls to `pyinfra.server.fact` asynchronously gathers the specific fact for all hosts if not already cached in `pyinfra._facts`
+ Finally, the command sets are run against each server asynchronously
