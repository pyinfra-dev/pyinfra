from typing_extensions import override

from pyinfra.api import FactBase


class RunitStatus(FactBase):
    """
    Returns a dict of name -> status for runit services.

    + service: optionally check only for a single service
    + svdir: alternative ``SVDIR``

    .. code:: python

        {
            'agetty-tty1': True,     # service is running
            'dhcpcd': False,         # service is down
            'wpa_supplicant': None,  # service is managed, but not running or down,
                                     # possibly in a fail state
        }
    """

    default = dict

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "sv"

    @override
    def command(self, service=None, svdir="/var/service") -> str:
        if service is None:
            return (
                'export SVDIR="{0}" && '
                'cd "$SVDIR" && find * -maxdepth 0 -exec sv status {{}} + 2>/dev/null'
            ).format(svdir)
        else:
            return 'SVDIR="{0}" sv status "{1}"'.format(svdir, service)

    @override
    def process(self, output):
        services = {}
        for line in output:
            statusstr, service, _ = line.split(sep=": ", maxsplit=2)
            status = None

            if statusstr == "run":
                status = True
            elif statusstr == "down":
                status = False
            # another observable state is "fail"
            # report as ``None`` for now

            services[service] = status

        return services


class RunitManaged(FactBase):
    """
    Returns a set of all services managed by runit

    + service: optionally check only for a single service
    + svdir: alternative ``SVDIR``
    """

    default = set

    @override
    def command(self, service=None, svdir="/var/service"):
        if service is None:
            return 'cd "{0}" && find -mindepth 1 -maxdepth 1 -type l -printf "%f\n"'.format(svdir)
        else:
            return 'cd "{0}" && test -h "{1}" && echo "{1}" || true'.format(svdir, service)

    @override
    def process(self, output):
        return set(output)
