'''
.. warning::

    This is a legacy module providing backwards compatibility. Please use the other modules:

    + :doc:`./systemd`
    + :doc:`./upstart`
    + :doc:`./launchd`
    + :doc:`./sysvinit`
    + :doc:`./bsdinit`
    + `server.service operation <server.html#server-service>`_
'''

from pyinfra import logger

from . import bsdinit, launchd, server, systemd, sysvinit, upstart


def _make_legacy_operation(legacy_op, op_func):
    def wrapper(*args, **kwargs):
        logger.warning((
            'The `init.{0}` operation is deprecated, '
            'please us the `{1}.{2}` operation.'
        ).format(
            legacy_op,
            op_func.__module__.replace('pyinfra.operations.', ''),
            op_func.__name__,
        ))
        return op_func(*args, **kwargs)

    wrapper._pyinfra_op = op_func
    return wrapper


d = _make_legacy_operation('d', sysvinit.service)
d_enable = _make_legacy_operation('d_enable', sysvinit.enable)
rc = _make_legacy_operation('rc', bsdinit.service)
upstart = _make_legacy_operation('upstart', upstart.service)
systemd = _make_legacy_operation('systemd', systemd.service)
launchd = _make_legacy_operation('launchd', launchd.service)
service = _make_legacy_operation('service', server.service)
