from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .sysvinit import InitdStatus


class RcdStatus(InitdStatus):
    """
    Same as ``initd_status`` but for BSD (/etc/rc.d) systems. Unlike Linux/init.d,
    BSD init scripts are well behaved and as such their output can be trusted.
    """

    @override
    def command(self) -> str:
        return """
            for SERVICE in `find /etc/rc.d /usr/local/etc/rc.d -type f`; do
                $SERVICE status 2> /dev/null || $SERVICE check 2> /dev/null
                echo "`basename $SERVICE`=$?"
            done
        """

    default = dict


class RcdEnabled(FactBase):
    """
    Returns a dict of OpenBSD rc.d services enabled at boot.
    """

    default = dict

    @override
    def requires_command(self) -> str:
        return "rcctl"

    @override
    def command(self) -> str:
        return "rcctl ls on"

    @override
    def process(self, output: list[str]) -> dict[str, bool]:
        return {line: True for line in output}
