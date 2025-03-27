# Writing Connectors

[Connectors](../connectors) enable pyinfra to directly integrate with other tools and systems. Connectors are written as Python classes.

Connectors come in three variations:

 - Inventory only
 - Execution only
 - Inventory and Execution

The last case just requires combining the two examples below and including any host/group gathering logic in `make_names_data`.

## Inventory Connector

Inventory connectors can return one or more hosts each invocation of `make_names_data`.

In the example below `make_names_data` is yielding a hostname, data, groups tuple. As long as the final `yield` is a tuple though, the gathered data
could be stored and processed in any data structure.

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
        # connect to api/parse files/process data here, resulting in a list of tuples;
        gathered_hosts = [
            ('@local', {}, ['@local']),
            ('foundhost', {'ip': 198.51.100.4}, ['remote', 'example'])
            ]

        for loop_host in gathered_hosts:
          yield gathered_hosts[0], gathered_hosts[1], gathered_hosts[2]
```

To use the inventory connector call `pyinfra @[name of connector in pyinfra.connectors] [deployment script].py`

The connector can also be run using `pyinfra @[name of connector in pyinfra.connectors]/[hostname] [deployment script].py`. If executed this way
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

## Where to make changes

Connectors enable pyinfra to expand work done `in its 5 stages <deploy-process.html#how-pyinfra-works>`_ by providing methods which can be called at
appropriate times.

To hook in to to the various steps with the methods outlined below.
```
--> Loading config...
--> Loading inventory...
```
`make_names_data` is used to supply inventory data about a host while at 'Loading inventory' stage.

Its worth being aware up front that due to `make_names_data` being a `staticmethod` it has no automatic access to the parent classes attributes.
To work around this - eg to configure an API connector - configuration will have to happen outside the function and be imported in. Two examples
(`getattr` and a function) are provided below.

```py
def load_settings():
  settings = {}
  # logic here
  return settings

class InventoryConnector(BaseConnector):
  api_instance = external.ApiClient()
  ...

  @staticmethod
  def make_names_data(_=None)
    api_client = getattr(InventoryConnector, 'api_instance')
    api_settings = load_settings()
    ...
```

```
--> Connecting to hosts...
    [pytest.example.com] Connected
```
`connect` can be used to check access to a host is possible. If the connection fails `ConnectError` should be raised with a message to display on
screen.

```
--> Preparing operations...
--> Preparing Operations...
    Loading: deploy_create_users.py
    [pytest.example.com] Ready: deploy_create_users.py

--> Detected changes:
[list of changes here]

--> Beginning operation run...
--> Starting operation: sshd_install.py | Install OpenSSH server
    [pytest.example.com] No changes
```

`run_shell_command`, `put_file`, `get_file` and `rsync` can be used to change behaviour of pyinfra as it performs operations.

```
--> Results:
    Operation                                                                                            Hosts   Success   Error   No Change
--> Disconnecting from hosts...
```

`disconnect` can be used after all operations complete to clean up any connection/s remaining to the hosts being managed.


## pyproject.toml

In order for pyinfra to gain knowledge about your connector, you need to add the following snippet to your connector's `pyproject.toml`:

```toml
[project.entry-points.'pyinfra.connectors']
# Key = Entry point name
# Value = module_path:class_name
custom = 'pyinfra_custom_connector.connector:LoggingConnector'
```

If modifying pyinfra directly, `pyinfra.connectors` should be added to `setup.py`.

