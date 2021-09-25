'''
Manage OpenVZ containers with ``vzctl``.
'''

import six

from pyinfra.api import operation, OperationError
from pyinfra.facts.vzctl import OpenvzContainers


@operation(is_idempotent=False)
def start(ctid, force=False, state=None, host=None):
    '''
    Start OpenVZ containers.

    + ctid: CTID of the container to start
    + force: whether to force container start
    '''

    args = ['{0}'.format(ctid)]

    if force:
        args.append('--force')

    yield 'vzctl start {0}'.format(' '.join(args))


@operation(is_idempotent=False)
def stop(ctid, state=None, host=None):
    '''
    Stop OpenVZ containers.

    + ctid: CTID of the container to stop
    '''

    args = ['{0}'.format(ctid)]

    yield 'vzctl stop {0}'.format(' '.join(args))


@operation(is_idempotent=False)
def restart(ctid, force=False, state=None, host=None):
    '''
    Restart OpenVZ containers.

    + ctid: CTID of the container to restart
    + force: whether to force container start
    '''

    yield stop(ctid, state=state, host=host)
    yield start(ctid, force=force, state=state, host=host)


@operation(is_idempotent=False)
def mount(ctid, state=None, host=None):
    '''
    Mount OpenVZ container filesystems.

    + ctid: CTID of the container to mount
    '''

    yield 'vzctl mount {0}'.format(ctid)


@operation(is_idempotent=False)
def unmount(ctid, state=None, host=None):
    '''
    Unmount OpenVZ container filesystems.

    + ctid: CTID of the container to unmount
    '''

    yield 'vzctl umount {0}'.format(ctid)


@operation(is_idempotent=False)
def delete(ctid, state=None, host=None):
    '''
    Delete OpenVZ containers.

    + ctid: CTID of the container to delete
    '''

    yield 'vzctl delete {0}'.format(ctid)


@operation(is_idempotent=False)
def create(ctid, template=None, state=None, host=None):
    '''
    Create OpenVZ containers.

    + ctid: CTID of the container to create
    '''

    # Check we don't already have a container with this CTID
    current_containers = host.get_fact(OpenvzContainers)
    if ctid in current_containers:
        raise OperationError(
            'An OpenVZ container with CTID {0} already exists'.format(ctid),
        )

    args = ['{0}'.format(ctid)]

    if template:
        args.append('--ostemplate {0}'.format(template))

    yield 'vzctl create {0}'.format(' '.join(args))


@operation(is_idempotent=False)
def set(ctid, save=True, state=None, host=None, **settings):
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
