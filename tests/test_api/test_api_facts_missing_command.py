"""
Tests for MissingCommandError / requires_command phase-aware behaviour.

When a fact declares ``requires_command`` and the requested binary is absent:

- **Prepare phase** – silent: the binary might not yet be installed.
  The fact must return ``default()`` so change-detection can proceed.
- **Execute phase** – compat shim (v3): warning logged, ``default()`` returned.
  Will raise ``MissingCommandError`` in v4.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from pyinfra.api.exceptions import FactError, FactNotCollected, MissingCommandError
from pyinfra.api.facts import _MISSING_COMMAND_MARKER, get_fact
from pyinfra.api.state import StateStage
from pyinfra.facts.zfs import ZfsPools


def _make_state(stage: StateStage) -> MagicMock:
    state = MagicMock()
    state.current_stage = stage
    return state


class TestMissingCommandPhaseAwareness(TestCase):
    """Phase-aware handling of MissingCommandError in the public get_fact() wrapper."""

    def test_prepare_phase_returns_default(self):
        """Binary absent during prepare → fact returns default() silently."""
        state = _make_state(StateStage.Prepare)
        host = MagicMock()

        with patch("pyinfra.api.facts._get_fact", side_effect=MissingCommandError("zpool")):
            result = get_fact(state, host, ZfsPools)

        assert result == ZfsPools().default()

    def test_execute_phase_returns_default_with_warning(self):
        """Binary absent during execute → compat shim: warning logged, default() returned (v3).
        TODO(v4): this should raise MissingCommandError instead."""
        state = _make_state(StateStage.Execute)
        host = MagicMock()

        with patch("pyinfra.api.facts._get_fact", side_effect=MissingCommandError("zpool")):
            result = get_fact(state, host, ZfsPools)

        assert result == ZfsPools().default()

    def test_missing_command_error_message(self):
        """MissingCommandError carries a human-readable message."""
        exc = MissingCommandError("zpool")
        assert "zpool" in str(exc)

    def test_missing_command_inherits_fact_not_collected(self):
        """MissingCommandError is a FactNotCollected (and a FactError)."""
        exc = MissingCommandError("zpool")
        assert isinstance(exc, FactNotCollected)
        assert isinstance(exc, FactError)


class TestMissingCommandMarker(TestCase):
    """The sentinel constant is stable – callers may depend on it."""

    def test_marker_is_unique_string(self):
        assert isinstance(_MISSING_COMMAND_MARKER, str)
        assert len(_MISSING_COMMAND_MARKER) > 0
        # Must not look like valid shell output from any standard command
        assert _MISSING_COMMAND_MARKER.startswith("##")
        assert _MISSING_COMMAND_MARKER.endswith("##")
