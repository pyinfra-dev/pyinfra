'''
Manage OpenVZ containers with ``vzctl``.
'''

import six

from pyinfra.api import operation, OperationError


@operation
def start(state, host, ctid, force=False):
    '''
    Start OpenVZ containers.

    + ctid: CTID of the container to start
    + force: whether to force container start
    '''

    args = ['{0}'.format(ctid)]

    if force:
        args.append('--force')

    yield 'vzctl start {0}'.format(' '.join(args))


@operation
def stop(state, host, ctid):
    '''
    Stop OpenVZ containers.

    + ctid: CTID of the container to stop
    '''

    args = ['{0}'.format(ctid)]

    yield 'vzctl stop {0}'.format(' '.join(args))


@operation
def restart(state, host, ctid, force=False):
    '''
    Restart OpenVZ containers.

    + ctid: CTID of the container to restart
    + force: whether to force container start
    '''

    yield stop(state, host, ctid)
    yield start(state, host, ctid, force=force)


@operation
def mount(state, host, ctid):
    '''
    Mount OpenVZ container filesystems.

    + ctid: CTID of the container to mount
    '''

    yield 'vzctl mount {0}'.format(ctid)


@operation
def unmount(state, host, ctid):
    '''
    Unmount OpenVZ container filesystems.

    + ctid: CTID of the container to unmount
    '''

    yield 'vzctl umount {0}'.format(ctid)


@operation
def delete(state, host, ctid):
    '''
    Delete OpenVZ containers.

    + ctid: CTID of the container to delete
    '''

    yield 'vzctl delete {0}'.format(ctid)


@operation
def create(state, host, ctid, template=None):
    '''
    Create OpenVZ containers.

    + ctid: CTID of the container to create
    '''

    # Check we don't already have a container with this CTID
    current_containers = host.fact.openvz_containers
    if ctid in current_containers:
        raise OperationError(
            'An OpenVZ container with CTID {0} already exists'.format(ctid),
        )

    args = ['{0}'.format(ctid)]

    if template:
        args.append('--ostemplate {0}'.format(template))

    yield 'vzctl create {0}'.format(' '.join(args))


@operation
def set(state, host, ctid, save=True, **settings):
    '''
    Set OpenVZ container details.

    + ctid: CTID of the container to set
    + save: whether to save the changes
    + settings: settings/arguments to apply to the container

    Settings/arguments:
        these are mapped directly to ``vztctl`` arguments, eg
        ``hostname='my-host.net'`` becomes ``--hostname my-host.net``.
    '''

    args = ['{0}'.format(ctid)]

    if save:
        args.append('--save')

    for key, value in six.iteritems(settings):
        # Handle list values (e.g. --nameserver X --nameserver X)
        if isinstance(value, list):
            args.extend('--{0} {1}'.format(key, v) for v in value)
        else:
            args.append('--{0} {1}'.format(key, value))

    yield 'vzctl set {0}'.format(' '.join(args))
