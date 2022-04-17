from pyinfra.api import operation


@operation(is_idempotent=False)
def agent(server=None, port=None):
    """
    Run puppet agent

    + server: master server URL
    + port: puppet master port

    Note: Either 'USE_SUDO_LOGIN=True' or 'USE_SU_LOGIN=True'
    for puppet.agent() as `puppet` is added to the path in
    the .bash_profile.

    **Example:**

    .. code:: python

        puppet.agent()

        # We also expect a return code of:
        # 0=no changes or 2=changes applied
        puppet.agent(
            name="Run the puppet agent",
            success_exit_codes=[0, 2],
        )

    """

    args = []

    if server:
        args.append("--server=%s" % server)
    if port:
        args.append("--masterport=%s" % port)

    yield "puppet agent -t %s" % " ".join(args)
