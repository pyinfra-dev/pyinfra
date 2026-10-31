"""
Manage processes controlled by supervisord using ``supervisorctl``.

Every operation accepts the global ``supervisorctl`` options: ``config_file``
(``-c``), ``server_url`` (``-s``), ``username`` (``-u``) and ``password``
(``-p``).

The read-only ``supervisorctl`` actions are facts, not operations: ``status``
maps to ``pyinfra.facts.supervisorctl.SupervisorctlStatus`` and ``pid`` to
``SupervisorctlPid`` / ``SupervisorctlPids``. The interactive actions
(``tail``, ``fg``, ``help``) are not covered.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.supervisorctl import SupervisorctlStatus, _make_supervisorctl_command


@operation()
def process(
    process: str,
    running: bool | None = True,
    restarted: bool = False,
    command: str | None = None,
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """
    Manage the state of supervisor processes.

    + process: name of the process to manage, a single ``<name>``, a group
      ``<gname>:*`` or ``all``
    + running: whether the process should be running
    + restarted: whether the process should be restarted
    + command: custom ``supervisorctl`` action to run like:
      ``supervisorctl <command> <process>``
    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)

    Processes in BACKOFF, FATAL or UNKNOWN state are considered not running.

    **Examples:**

    .. code:: python

        from pyinfra.operations import supervisorctl

        supervisorctl.process(
            name="Start the web process",
            process="web",
            running=True,
        )

        supervisorctl.process(
            name="Restart every process in the workers group",
            process="workers:*",
            restarted=True,
        )

    """

    # This mirrors operations.util.service.handle_service_control, which cannot
    # be reused here: its format-string API cannot carry a HiddenValue password
    # without leaking it into logs.
    supervisorctl_command = _make_supervisorctl_command(
        config_file=config_file,
        server_url=server_url,
        username=username,
        password=password,
    )

    statuses = host.get_fact(
        SupervisorctlStatus,
        config_file=config_file,
        server_url=server_url,
        username=username,
        password=password,
    )

    if process == "all" or process.endswith(":*"):
        if process == "all":
            members = list(statuses)
        else:
            members = [name for name in statuses if name.startswith(process[:-1])]
        is_running = any(statuses.get(name) is True for name in members)
        is_fully_running = bool(members) and all(statuses.get(name) is True for name in members)
    else:
        is_running = statuses.get(process) is True
        is_fully_running = is_running

    # Need down but running
    if running is False:
        if is_running:
            yield StringCommand(supervisorctl_command, "stop", QuoteString(process))
        else:
            host.noop(f"process {process} is stopped")

    # Need running but down
    if running is True:
        if is_fully_running:
            host.noop(f"process {process} is running")
        else:
            yield StringCommand(supervisorctl_command, "start", QuoteString(process))

    # Only restart if the process is already running
    if restarted and is_running:
        yield StringCommand(supervisorctl_command, "restart", QuoteString(process))

    # Always execute arbitrary commands as these may or may not rely on the
    # process being up or down
    if command is not None:
        yield StringCommand(supervisorctl_command, QuoteString(command), QuoteString(process))


@operation(is_idempotent=False)
def reread(
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """
    Reload the supervisord configuration files, without adding, removing or
    restarting anything.

    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)
    """

    yield StringCommand(
        _make_supervisorctl_command(
            config_file=config_file,
            server_url=server_url,
            username=username,
            password=password,
        ),
        "reread",
    )


@operation(is_idempotent=False)
def update(
    groups: list[str] | None = None,
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """
    Reload the supervisord configuration files, add/remove process groups as
    necessary and restart affected programs.

    + groups: optional list of process groups to update, defaults to all
    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)

    **Example:**

    .. code:: python

        from pyinfra.operations import supervisorctl

        supervisorctl.update(
            name="Apply config changes to the workers group",
            groups=["workers"],
        )

    """

    command_bits: list[StringCommand | str | QuoteString] = [
        _make_supervisorctl_command(
            config_file=config_file,
            server_url=server_url,
            username=username,
            password=password,
        ),
        "update",
    ]

    if groups is not None:
        command_bits.extend(QuoteString(group) for group in groups)

    yield StringCommand(*command_bits)


@operation(is_idempotent=False)
def reload(
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """
    Restart the remote supervisord.

    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)
    """

    yield StringCommand(
        _make_supervisorctl_command(
            config_file=config_file,
            server_url=server_url,
            username=username,
            password=password,
        ),
        "reload",
    )


@operation(is_idempotent=False)
def add(
    name: str,
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """
    Activate any updates in config for a process or group.

    + name: name of the process/group to add
    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)
    """

    yield StringCommand(
        _make_supervisorctl_command(
            config_file=config_file,
            server_url=server_url,
            username=username,
            password=password,
        ),
        "add",
        QuoteString(name),
    )


@operation(is_idempotent=False)
def remove(
    name: str,
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """
    Remove a process or group from the active configuration.

    + name: name of the process/group to remove
    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)
    """

    yield StringCommand(
        _make_supervisorctl_command(
            config_file=config_file,
            server_url=server_url,
            username=username,
            password=password,
        ),
        "remove",
        QuoteString(name),
    )


@operation(is_idempotent=False)
def clear(
    process: str,
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """
    Clear the log files of a process.

    + process: name of the process, or ``all`` to clear every process' logs
    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)
    """

    yield StringCommand(
        _make_supervisorctl_command(
            config_file=config_file,
            server_url=server_url,
            username=username,
            password=password,
        ),
        "clear",
        QuoteString(process),
    )


@operation(is_idempotent=False)
def signal(
    signal: str,
    process: str,
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """
    Send a signal to a supervisor process.

    + signal: signal to send, eg ``HUP`` or ``USR2``
    + process: name of the process to signal, a single ``<name>``, a group
      ``<gname>:*`` or ``all``
    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)

    **Example:**

    .. code:: python

        from pyinfra.operations import supervisorctl

        supervisorctl.signal(
            name="Rotate web process logs",
            signal="USR2",
            process="web",
        )

    """

    yield StringCommand(
        _make_supervisorctl_command(
            config_file=config_file,
            server_url=server_url,
            username=username,
            password=password,
        ),
        "signal",
        QuoteString(signal),
        QuoteString(process),
    )
