from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase


class FlatpakBaseFact(FactBase):
    abstract = True

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "flatpak"


class FlatpakPackage(FlatpakBaseFact):
    """
    Returns information for an installed flatpak package

    .. code:: python

        {
            "id": "org.signal.Signal",
            "ref": "app/org.signal.Signal/x86_64/stable",
            "version": "7.12.0"
        }
    """

    default = dict
    _regexes = {
        "id": "^[ ]+ID:[ ]+(.*)$",
        "ref": r"^[ ]+Ref:[ ]+(.*)$",
        "version": r"^[ ]+Version:[ ]+([\w\d.-]+).*$",
    }

    @override
    def command(self, package):
        return f"flatpak info {package}"

    @override
    def process(self, output):
        data = {}
        for line in output:
            for regex_name, regex in self._regexes.items():
                matches = re.match(regex, line)
                if matches:
                    data[regex_name] = matches.group(1)

        return data


class FlatpakPackages(FlatpakBaseFact):
    """
    Returns a list of installed flatpak packages:

    .. code:: python

        [
            "org.gnome.Platform",
            "org.kde.Platform",
            "org.kde.Sdk",
            "org.libreoffice.LibreOffice",
            "org.videolan.VLC"
        ]
    """

    default = list

    @override
    def command(self):
        return "flatpak list --columns=application"

    @override
    def process(self, output):
        return [flatpak for flatpak in output[1:]]
