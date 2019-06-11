from pyinfra.api import operation


@operation
def agent(state, host, server=None, port=None):
    '''
    Run puppet agent

    + server: master server URL
    + port: puppet master port
    '''

    args = []

    if server:
        args.append('--server=%s' % server)
    if port:
        args.append('--masterport=%s' % port)

    yield 'puppet agent -t %s' % ' '.join(args)
