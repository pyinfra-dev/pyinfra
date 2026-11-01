from __future__ import annotations

from pyinfra.api import QuoteString, StringCommand, operation


@operation(is_idempotent=False)
def agent(server: str | None = None, port: int | None = None):
    """
    Run puppet agent

    + server: master server URL
    + port: puppet master port

    Note: Either 'USE_SUDO_LOGIN=True' or 'USE_SU_LOGIN=True'
    for puppet.agent() as `puppet` is added to the path in
    the .bash_profile.

    **Example:**

    .. code:: python

        from pyinfra.operations import puppet
        puppet.agent()

        # We also expect a return code of:
        # 0=no changes or 2=changes applied
        puppet.agent(
            name="Run the puppet agent",
            success_exit_codes=[0, 2],
        )

    """

    command: list[str | QuoteString] = ["puppet agent -t"]

    if server:
        command.append(QuoteString(f"--server={server}"))
    if port:
        command.append(QuoteString(f"--masterport={port}"))

    yield StringCommand(*command)
