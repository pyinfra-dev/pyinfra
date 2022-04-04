# Writing Connectors

[Connectors](../connectors) enable `pyinfra` to directly integrate with other tools and systems. These do not require the other system to have any knowledge of `pyinfra`.

Check out [the existing code](https://github.com/Fizzadar/pyinfra/tree/master/pyinfra/api/connectors). Be sure to add tests and documentation.

All connectors must provide the `make_names_data` function:

```py
def make_names_data(hostname=None):
    '''
    Generate list of hosts.

    Args:
        hostname (string): the string after the `@connector/` inventory name

    Yields:
        tuple: (name, data, group_names)
    '''

    yield 'name-of-host', {'key': 'value'}, ['a-group', 'another-group']
```

Furthermore, connectors that modify execution must provide the following functions:

```py
from .util import split_combined_output

EXECUTION_CONNECTOR = True  # flag this connector as defining execution


def connect(state, host):
    '''
    Connect to the target host.

    Args
        state (``pyinfra.api.State`` object): state object for this command
        host (``pyinfra.api.Host`` object): the target host:

    Returns:
        status (boolean)
    '''

    return True


def run_shell_command(
    state, host, command,
    get_pty=False,
    timeout=None,
    stdin=None,
    success_exit_codes=None,
    print_output=False,
    print_input=False,
    return_combined_output=False,
    use_sudo_password=False,
    **command_kwargs
):
    '''
    Execute a (shell) command on the target host.

    Args:
        state (``pyinfra.api.State`` object): state object for this command
        host (``pyinfra.api.Host`` object): the target host
        command (string): actual command to execute

    Returns:
        tuple: (exit_code, stdout, stderr)
        stdout and stderr are both lists of strings from each buffer.
    '''

    status = True
    combined_output = [
        ('stdout', 'some standard output'),
        ('stderr', 'some standard error'),
        ('stderr', 'some more standard error'),
    ]

    if return_combined_output:
        return status, combined_output

    stdout, stderr = split_combined_output(combined_output)
    return status, stdout, stderr


def put_file(
    state, host, filename_or_io, remote_filename,
    print_output=False, print_input=False,
    **command_kwargs
):
    '''
    Upload a local file or IO object to the target host.

    Returns:
        status (boolean)
    '''

    return True


def get_file(
    state, host, remote_filename, filename_or_io,
    print_output=False, print_input=False,
    **command_kwargs
):
    '''
    Download a remote file to a local file or IO object.

    Returns:
        status (boolean)
    '''

    return True
```
