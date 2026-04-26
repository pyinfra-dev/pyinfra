"""
Tests for FactPreconditionError / check_preconditions() phase-aware behaviour.

When a fact's ``check_preconditions()`` method returns a reason string:

- **Prepare phase** – silent: the condition might not yet be satisfied (e.g. a
  kernel module not yet loaded).  The fact must return ``default()``.
- **Execute phase** – loud: ``check_preconditions`` is a new API so no existing
  deploys rely on it.  The exception propagates so the developer gets a clear
  error about incorrect deploy ordering.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from pyinfra.api.exceptions import FactError, FactNotCollected, FactPreconditionError
from pyinfra.api.facts import get_fact
from pyinfra.api.state import StateStage
from pyinfra.facts.zfs import ZfsPools


def _make_state(stage: StateStage) -> MagicMock:
    state = MagicMock()
    state.current_stage = stage
    return state


class TestFactPreconditionError(TestCase):
    """Phase-aware handling of FactPreconditionError via check_preconditions() in get_fact()."""

    def test_prepare_phase_returns_default(self):
        """Precondition not satisfied during prepare → fact returns default() silently."""
        state = _make_state(StateStage.Prepare)
        host = MagicMock()

        with patch(
            "pyinfra.api.facts._get_fact",
            side_effect=FactPreconditionError(ZfsPools, "zfs module not loaded"),
        ):
            result = get_fact(state, host, ZfsPools)

        assert result == ZfsPools().default()

    def test_execute_phase_raises(self):
        """Precondition not satisfied during execute → FactPreconditionError propagates."""
        state = _make_state(StateStage.Execute)
        host = MagicMock()

        with patch(
            "pyinfra.api.facts._get_fact",
            side_effect=FactPreconditionError(ZfsPools, "zfs module not loaded"),
        ):
            with self.assertRaises(FactPreconditionError) as ctx:
                get_fact(state, host, ZfsPools)

        assert ctx.exception.fact_cls is ZfsPools
        assert "zfs module not loaded" in ctx.exception.reason

    def test_precondition_error_message(self):
        """FactPreconditionError carries a human-readable message."""
        exc = FactPreconditionError(ZfsPools, "module not loaded")
        assert "ZfsPools" in str(exc)
        assert "module not loaded" in str(exc)

    def test_precondition_error_inherits_fact_not_collected(self):
        """FactPreconditionError is a FactNotCollected (and a FactError)."""
        exc = FactPreconditionError(ZfsPools, "reason")
        assert isinstance(exc, FactNotCollected)
        assert isinstance(exc, FactError)
