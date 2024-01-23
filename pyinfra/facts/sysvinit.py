from __future__ import annotations

import re
from typing import Optional

from pyinfra.api import FactBase


class InitdStatus(FactBase):
    """
    Low level check for every /etc/init.d/* script. Unfortunately many of these
    misbehave and return exit status 0 while also displaying the help info/not
    offering status support.

    Returns a dict of name -> status.

    Expected codes found at:
        http://refspecs.linuxbase.org/LSB_3.1.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html
    """

    command = """
        for SERVICE in `ls /etc/init.d/`; do
            _=`cat /etc/init.d/$SERVICE | grep "### BEGIN INIT INFO"`

            if [ "$?" = "0" ]; then
                STATUS=`/etc/init.d/$SERVICE status`
                echo "$SERVICE=$?"
            fi
        done
    """

    regex = r"([a-zA-Z0-9\-]+)=([0-9]+)"
    default = dict

    def process(self, output) -> dict[str, Optional[bool]]:
        services: dict[str, Optional[bool]] = {}

        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                intstatus = int(matches.group(2))
                status: Optional[bool] = None

                # Exit code 0 = OK/running
                if intstatus == 0:
                    status = True

                # Exit codes 1-3 = DOWN/not running
                elif intstatus < 4:
                    status = False

                services[matches.group(1)] = status

        return services
