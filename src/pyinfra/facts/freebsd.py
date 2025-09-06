from __future__ import annotations

from typing_extensions import Optional, override

from pyinfra.api import FactBase
from pyinfra.api.command import QuoteString, StringCommand, make_formatted_string_command


class ServiceScript(FactBase):
    @override
    def command(self, srvname: str, jail: Optional[str] = None) -> StringCommand:
        if jail is None:
            jail = ""

        return make_formatted_string_command(
            (
                "for service in `service -j {0} -l`; do "
                'if [ {1} = \\"$service\\" ]; '
                'then echo \\"$service\\"; '
                "fi; "
                "done"
            ),
            QuoteString(jail),
            QuoteString(srvname),
        )


class ServiceStatus(FactBase):
    @override
    def command(self, srvname: str, jail: Optional[str] = None) -> StringCommand:
        if jail is None:
            jail = ""

        return make_formatted_string_command(
            (
                "service -j {0} {1} status > /dev/null 2>&1; "
                "if [ $? -eq 0 ]; then "
                "echo running; "
                "fi"
            ),
            QuoteString(jail),
            QuoteString(srvname),
        )


class Sysrc(FactBase):
    @override
    def command(self, parameter: str, jail: Optional[str] = None) -> StringCommand:
        if jail is None:
            command = make_formatted_string_command(
                ("sysrc -in -- {0} || true"), QuoteString(parameter)
            )
        else:
            command = make_formatted_string_command(
                ("sysrc -j {0} -in -- {1} || true"), QuoteString(jail), QuoteString(parameter)
            )

        return command


class PkgPackage(FactBase):
    @override
    def command(self, package: str, jail: Optional[str] = None) -> StringCommand:
        if jail is None:
            command = make_formatted_string_command(
                ("pkg info -E -- {0} 2> /dev/null || true"), QuoteString(package)
            )
        else:
            command = make_formatted_string_command(
                ("pkg -j {0} info -E -- {1} 2> /dev/null || true"),
                QuoteString(jail),
                QuoteString(package),
            )

        return command
