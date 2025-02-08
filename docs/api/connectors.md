# Writing Connectors

[Connectors](../connectors) enable pyinfra to directly integrate with other tools and systems. Connectors are written as Python classes.

## Inventory Connector

Inventory connectors can return one or more hosts each invocation of `make_names_data`.

In the example below `make_names_data` is yielding a fixed hostname, data, groups tuple without processing. It could also be querying an API for hosts
then looping over them, returning a dynamic hostname, data, groups list tuple based on what it gathers from the remote end (note in that case hosts
have to be looped and yielded one at a time).

```py
class InventoryConnector(BaseConnector):
    handles_execution = False

    @staticmethod
    def make_names_data(_=None):
        """
        Generate inventory targets.

        Yields:
            tuple: (name, data, groups)
        """
        yield "@local", {}, ["@local"]
```

To use the inventory connector call `pyinfra @[name of connector in pyinfra.connectors] [deployment script].py`

The conector can also be run using `pyinfra @[name of connector in pyinfra.connectors]/[hostname] [deployment script].py`. If executed this way
(inventory/data requested for a single host), `make_names_data(_=None)` should be updated to `make_names_data(name)` and the `name == None` case
handled in code separately from `name` being a valid string.


## Executing Connector

A connector that implements execution requires a few more methods:

```py
class LocalConnector(BaseConnector):
    handles_execution = True

    @staticmethod
    def make_names_data(_=None):
        # Unlike InventoryConnector above, this connector can only return one host each invocation of make_names_data().

        ...  # see above
 
    def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> Tuple[bool, CommandOutput]:
        """
        Execute a command on the local machine.

        Args:
            command (StringCommand): actual command to execute
            print_output (bool): whether to print command output
            print_input (bool): whether to print command input
            arguments: (ConnectorArguments): connector global arguments

        Returns:
            tuple: (bool, CommandOutput)
            Bool indicating success and CommandOutput with stdout/stderr lines.
        """

    def put_file(
        self,
        filename_or_io,
        remote_filename,
        remote_temp_filename=None,  # ignored
        print_output: bool = False,
        print_input: bool = False,
        **arguments,
    ) -> bool:
        """
        Upload a local file or IO object by copying it to a temporary directory
        and then writing it to the upload location.

        Returns:
            bool: indicating success or failure.
        """

    def get_file(
        self,
        remote_filename,
        filename_or_io,
        remote_temp_filename=None,  # ignored
        print_output: bool = False,
        print_input: bool = False,
        **arguments,
    ) -> bool:
        """
        Download a local file by copying it to a temporary location and then writing
        it to our filename or IO object.

        Returns:
            bool: indicating success or failure.
        """
```

## pyproject.toml

In order for pyinfra to gain knowledge about your connector, you need to add the following snippet to your connector's `pyproject.toml`:

```toml
[project.entry-points.'pyinfra.connectors']
# Key = Entry point name
# Value = module_path:class_name
custom = 'pyinfra_custom_connector.connector:LoggingConnector'
```

If modifying pyinfra directly, `pyinfra.connectors` should be added to `setup.py`.

For quick and dirty testing of a new connector add the connect to `pyinfra/pyinfra-*.dist-info/entry_points.txt`.

