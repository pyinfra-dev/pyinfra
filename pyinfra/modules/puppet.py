from pyinfra.api import operation


@operation
def agent(state, host, server=None, port=None):
    '''
    Run puppet agent

    + server: master server URL
    + port: puppet master port

    Note: Either 'USE_SUDO_LOGIN=True' or 'USE_SU_LOGIN=True'
    for puppet.agent() as `puppet` is added to the path in
    the .bash_profile.

    Example:

    .. code:: python

        puppet.agent()

    '''

    args = []

    if server:
        args.append('--server=%s' % server)
    if port:
        args.append('--masterport=%s' % port)

    yield 'puppet agent -t %s' % ' '.join(args)
