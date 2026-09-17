from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from rich.errors import LiveError
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from pyinfra.api.output import get_console, is_output_active

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

# A single shared Progress instance is reused for the whole run so that
# concurrent/nested phases (connect, prepare, execute, ...) each get their own
# bar within one live display. Per-host log lines printed via the shared
# console appear *above* the live bars automatically.
#
# The module-level refcount is mutated from multiple greenlets without a lock;
# this is safe because greenlets are cooperative and ``auto_refresh=False``
# means there is no background refresh thread racing the mutations.
_progress: Progress | None = None
_active_spinners = 0


def _get_progress() -> Progress:
    global _progress
    if _progress is None:
        _progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=get_console(),
            transient=True,
            auto_refresh=False,
        )
    return _progress


def _spinner_enabled() -> bool:
    # Only render when in CLI mode and not explicitly disabled.
    return is_output_active() and os.environ.get("PYINFRA_PROGRESS") != "off"


def _noop_progress(complete_item: Any) -> None:
    pass


@contextmanager
def progress_spinner(
    items: Iterable[Any],
    prefix_message: str | None = None,
) -> Iterator[Callable[[Any], None]]:
    """
    Display a Rich progress bar while ``items`` are completed.

    Yields a ``progress(complete_item)`` callback; callers may ignore it (using
    the bar purely as a "busy" indicator). Multiple/nested calls share a single
    live display, each contributing its own bar. The display is refreshed
    manually (``auto_refresh=False``) from the callback to stay well-behaved
    under gevent (no background refresh greenlet).
    """
    if not _spinner_enabled():
        yield _noop_progress
        return

    global _active_spinners, _progress

    if not isinstance(items, set):
        items = set(items)

    total_items = len(items)
    progress_bar = _get_progress()

    if _active_spinners == 0:
        try:
            progress_bar.start()
        except LiveError:
            # Another live display owns the shared console (e.g. the CLI's
            # live progress tree) — rich only allows one at a time.
            _progress = None
            yield _noop_progress
            return
    _active_spinners += 1

    description = prefix_message or "Working"
    task_id = progress_bar.add_task(description, total=total_items)
    progress_bar.refresh()

    def progress(complete_item: Any) -> None:
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
        # Decrement first so the display is always stopped even if the task
        # removal fails.
        _active_spinners -= 1
        try:
            progress_bar.remove_task(task_id)
            progress_bar.refresh()
        finally:
            if _active_spinners == 0:
                progress_bar.stop()
                # Drop the instance so a fresh one is created for the next run
                # (important for long-lived processes / tests).
                _progress = None
