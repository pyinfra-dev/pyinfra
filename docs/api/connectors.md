# Writing Connectors

[Connectors](../connectors) enable pyinfra to directly integrate with other tools and systems. Connectos are written as Python classes.

## Inventory Connector

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

## Executing Connector

A connector that implements execution requires a few more methods:

```py
class LocalConnector(BaseConnector):
    handles_execution = True

    @staticmethod
    def make_names_data(_=None):
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
            bool: indicating succes or failure.
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