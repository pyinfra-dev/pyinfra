"""
Manipulate system rc files.
"""

from __future__ import annotations

from typing_extensions import List, Optional, Union

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.api.exceptions import OperationValueError
from pyinfra.facts.freebsd import Sysrc

SYSRC_ADD: str = "add"
SYSRC_SUB: str = "sub"
SYSRC_SET: str = "set"
SYSRC_DEL: str = "del"


@operation()
def sysrc(
    parameter: str,
    value: str,
    jail: Optional[str] = None,
    command: str = SYSRC_SET,
    overwrite: bool = False,
):
    """
    Safely edit system rc files.

    + parameter: Parameter to manipulate.
    + value: Value, if the parameter requires it.
    + jail: See ``-j`` in ``sysrc(8)``.
    + command: Desire state of the parameter.
    + overwrite: Overwrite the value of the parameter when ``command`` is set to ``set``.

    Commands:
        There are a few commands you can use to manipulate the rc file:

        - add: Adds the value to the parameter.
        - sub: Delete the parameter value.
        - set: Change the parameter value. If the parameter already has a value
               set, the changes will not be applied unless ``overwrite`` is set
               to ``True``.
        - del: Delete the parameter.

    **Example:**

    .. code:: python

        sysrc.sysrc(
            "beanstalkd_enable",
            "YES",
            command="set"
        )
    """

    args: List[Union[str, "QuoteString"]] = []

    args.extend(["sysrc", "-i"])

    if command == SYSRC_DEL:
        sign = "="

        if not host.get_fact(Sysrc, parameter=parameter, jail=jail):
            host.noop(f"Cannot find sysrc(8) parameter '{parameter}'")
            return

        args.append("-x")

    elif command == SYSRC_SET:
        sign = "="

        if not overwrite and host.get_fact(Sysrc, parameter=parameter, jail=jail):
            host.noop(f"sysrc(8) parameter '{parameter}' already set")
            return

    elif command == SYSRC_ADD:
        sign = "+="

    elif command == SYSRC_SUB:
        sign = "-="

    else:
        raise OperationValueError(f"Invalid sysrc command: {command}")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["--", QuoteString(f"{parameter}{sign}{value}")])

    yield StringCommand(*args)
