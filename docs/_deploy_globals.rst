
Privilege & user escalation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. caution::
    When combining privilege escalation arguments it is important to know the order they
    are applied: ``doas`` -> ``sudo`` -> ``su``. For example
    ``_sudo=True,_su_user="pyinfra"`` yields a command like ``sudo su pyinfra..``.

.. list-table::
   :header-rows: 1
   :widths: 25 45 15 15

   * - Key
     - Description
     - Type
     - Default
   * - ``_sudo``
     - Execute/apply any changes with sudo.
     - ``bool``
     - ``False``

   * - ``_sudo_user``
     - Execute/apply any changes with sudo as a non-root user.
     - ``str``
     - 

   * - ``_use_sudo_login``
     - Execute sudo with a login shell.
     - ``bool``
     - ``False``

   * - ``_sudo_password``
     - Password to sudo with. If needed and not specified pyinfra will prompt for it.
     - ``str``
     - 

   * - ``_preserve_sudo_env``
     - Preserve the shell environment of the connecting user when using sudo.
     - ``bool``
     - ``False``

   * - ``_su_user``
     - Execute/apply any changes with this user using su.
     - ``str``
     - 

   * - ``_use_su_login``
     - Execute su with a login shell.
     - ``bool``
     - ``False``

   * - ``_preserve_su_env``
     - Preserve the shell environment of the connecting user when using su.
     - ``bool``
     - ``False``

   * - ``_su_shell``
     - Use this shell (instead of user login shell) when using ``_su``). Only available under Linux, for use when using `su` with a user that has nologin/similar as their login shell.
     - ``str``
     - ``False``

   * - ``_su_password``
     - Password to su with.
     - ``str``
     - 

   * - ``_doas``
     - Execute/apply any changes with doas.
     - ``bool``
     - ``False``

   * - ``_doas_user``
     - Execute/apply any changes with doas as a non-root user.
     - ``str``
     - 

**Examples:**

.. code:: python

    # Execute a command with sudo
    server.user(
        name="Create pyinfra user using sudo",
        user="pyinfra",
        _sudo=True,
    )

    # Execute a command with a specific sudo password
    server.user(
        name="Create pyinfra user using sudo",
        user="pyinfra",
        _sudo=True,
        _sudo_password="my-secret-password",
    )

Shell control & features
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 45 15 15

   * - Key
     - Description
     - Type
     - Default
   * - ``_shell_executable``
     - The shell executable to use for executing commands.
     - ``str``
     - ``sh``

   * - ``_chdir``
     - Directory to switch to before executing the command.
     - ``str``
     - 

   * - ``_env``
     - Dictionary of environment variables to set.
     - ``Mapping[str, str]``
     - ``{}``

   * - ``_success_exit_codes``
     - List of exit codes to consider a success.
     - ``Iterable[int]``
     - ``[0]``

   * - ``_timeout``
     - Timeout for *each* command executed during the operation.
     - ``int``
     - 

   * - ``_get_pty``
     - Whether to get a pseudoTTY when executing any commands.
     - ``bool``
     - ``False``

   * - ``_stdin``
     - String or buffer to send to the stdin of any commands.
     - ``Union[str, list, Iterable]``
     - 

   * - ``_temp_dir``
     - Temporary directory on the remote host for file operations.
     - ``str``
     - 

**Examples:**

.. code:: python

    # Execute from a specific directory
    server.shell(
        name="Bootstrap nginx params",
        commands=["openssl dhparam -out dhparam.pem 4096"],
        _chdir="/etc/ssl/certs",
    )

Operation meta & callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 45 15 15

   * - Key
     - Description
     - Type
     - Default
   * - ``name``
     - Name of the operation.
     - ``str``
     - 

   * - ``_ignore_errors``
     - Ignore errors when executing the operation.
     - ``bool``
     - ``False``

   * - ``_continue_on_error``
     - Continue executing operation commands after error. Only applies when ``_ignore_errors`` is true.
     - ``bool``
     - ``False``

   * - ``_if``
     - Only run this operation if these functions return True
     - ``Union[List, Callable, NoneType]``
     - ``[]``


Execution strategy
~~~~~~~~~~~~~~~~~~

Execution strategy arguments control how pyinfra executes operations across the inventory.
For example, you can run operations in parallel, serially, or skip idempotency checks.

.. list-table::
   :header-rows: 1
   :widths: 25 45 15 15

   * - Key
     - Description
     - Type
     - Default
   * - ``_parallel``
     - Run this operation in batches of hosts.
     - ``int``
     - ``0``

   * - ``_run_once``
     - Only execute this operation once, on the first host to see it.
     - ``bool``
     - ``False``

   * - ``_serial``
     - Run this operation host by host, rather than in parallel.
     - ``bool``
     - ``False``

   * - ``_execution_only``
     - Skip idempotency checks for this operation.
     - ``bool``
     - ``False``

**Examples:**

.. code:: python

    # Run this operation serially
    server.shell(
        name="Run script serially",
        commands=["/opt/script.sh"],
        _serial=True,
    )

    # Skip idempotency checks and always execute this operation
    server.shell(
        name="Always run script",
        commands=["/opt/script.sh"],
        _execution_only=True,
    )

Retry behavior
~~~~~~~~~~~~~~

Retry arguments allow you to automatically retry operations that fail. You can specify
how many times to retry, the delay between retries, and optionally a condition
function to determine when to stop retrying.

.. list-table::
   :header-rows: 1
   :widths: 25 45 15 15

   * - Key
     - Description
     - Type
     - Default
   * - ``_retries``
     - Number of times to retry failed operations.
     - ``int``
     - ``0``

   * - ``_retry_delay``
     - Delay in seconds between retry attempts.
     - ``Union[int, float]``
     - ``5``

   * - ``_retry_until``
     - Callable taking output data that returns True to continue retrying.
     - ``Callable[dict, bool]``
     - 

**Examples:**

.. code:: python

    # Retry a command up to 3 times with the default 5 second delay
    server.shell(
        name="Run flaky command with retries",
        commands=["flaky_command"],
        _retries=3,
    )
    # Retry with a custom delay
    server.shell(
        name="Run flaky command with custom delay",
        commands=["flaky_command"],
        _retries=2,
        _retry_delay=10,  # 10 second delay between retries
    )
    # Retry with a custom condition
    def retry_on_specific_error(output_data):
        # Retry if stderr contains "temporary failure"
        for line in output_data["stderr_lines"]:
            if "temporary failure" in line.lower():
                return True
        return False

    server.shell(
        name="Run command with conditional retry",
        commands=["flaky_command"],
        _retries=5,
        _retry_until=retry_on_specific_error,
    )