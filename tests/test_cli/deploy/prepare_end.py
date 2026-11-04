import json
import os

from pyinfra import state
from pyinfra.api import BaseStateCallback


class _PrepareEndProbe(BaseStateCallback):
    """Record the arguments each ``prepare_end`` call receives.

    The recorder appends one JSON object per call to the file named by the
    ``PYINFRA_PREPARE_END_FILE`` environment variable, so a test can inspect
    what the hook saw without reaching into the state object.
    """

    def prepare_end(self, state, dry=False, debug=False):
        path = os.environ.get("PYINFRA_PREPARE_END_FILE")
        if path:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"dry": dry, "debug": debug}) + "\n")


state.add_callback_handler(_PrepareEndProbe())
