"""
Fetch and install binary updates to FreeBSD.
"""

from __future__ import annotations


from pyinfra.api import QuoteString, StringCommand, operation


@operation()
def update(
    force: bool = False,
    basedir: str | None = None,
    workdir: str | None = None,
    conffile: str | None = None,
    jail: str | None = None,
    key: str | None = None,
    currently_running: str | None = None,
    server: str | None = None,
):
    """
    Based on the currently installed world and the configuration options set, fetch
    all available binary updates and install them.

    + force: See ``-F`` in ``freebsd-update(8)``.
    + basedir: See ``-b`` in ``freebsd-update(8)``.
    + workdir: See ``-d`` in ``freebsd-update(8)``.
    + conffile: See ``-f`` in ``freebsd-update(8)``.
    + jail: See ``-j`` in ``freebsd-update(8)``.
    + key: See ``-k`` in ``freebsd-update(8)``.
    + currently_running: See ``--currently-running`` in ``freebsd-update(8)``.
    + server: See ``-s`` in ``freebsd-update(8)``.

    **Example:**

    .. code:: python

        freebsd_update.update()
    """

    args: list[str | QuoteString] = []

    args.extend(["PAGER=cat", "freebsd-update", "--not-running-from-cron"])

    if force:
        args.append("-F")

    if basedir is not None:
        args.extend(["-b", QuoteString(basedir)])

    if workdir is not None:
        args.extend(["-d", QuoteString(workdir)])

    if conffile is not None:
        args.extend(["-f", QuoteString(conffile)])

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    if key is not None:
        args.extend(["-k", QuoteString(key)])

    if server is not None:
        args.extend(["-s", QuoteString(server)])

    args.extend(["fetch", "install"])

    yield StringCommand(*args)
