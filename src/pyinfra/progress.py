import os
from contextlib import contextmanager

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from pyinfra.api.output import get_console, is_output_active


@contextmanager
def progress_spinner(items, prefix_message=None):
    """
    Display a Rich progress spinner while ``items`` are completed.

    Yields a ``progress(complete_item)`` callback; callers may ignore it (using
    the spinner purely as a "busy" indicator).  The display is refreshed
    manually (``auto_refresh=False``) from the callback to stay well-behaved
    under gevent (no background refresh greenlet).
    """
    # If there's no active output we're not in CLI mode, so return a noop
    # handler and exit.
    if not is_output_active():
        yield lambda complete_item: None
        return

    # Allow disabling the spinner entirely.
    if os.environ.get("PYINFRA_PROGRESS") == "off":
        yield lambda complete_item: None
        return

    if not isinstance(items, set):
        items = set(items)

    total_items = len(items)
    console = get_console()

    columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ]
    if total_items > 1:
        columns.append(BarColumn())
        columns.append(TextColumn("{task.completed}/{task.total}"))

    progress_bar = Progress(
        *columns,
        console=console,
        transient=True,
        auto_refresh=False,
    )

    description = prefix_message or "Working"
    task_id = progress_bar.add_task(description, total=total_items)

    progress_bar.start()
    progress_bar.refresh()

    def progress(complete_item):
        if complete_item not in items:
            raise ValueError(
                f"Invalid complete item: {complete_item} not in {items}",
            )
        items.remove(complete_item)
        progress_bar.update(task_id, advance=1)
        progress_bar.refresh()

    try:
        yield progress
    finally:
        progress_bar.stop()
