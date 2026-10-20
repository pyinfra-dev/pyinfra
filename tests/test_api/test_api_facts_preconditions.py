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
from pyinfra.api.facts import FactBase, get_fact
from pyinfra.connectors.util import CommandOutput, OutputLine
from pyinfra.facts.zfs import ZfsPools


def _make_state(is_executing: bool) -> MagicMock:
    state = MagicMock()
    state.is_executing = is_executing
    return state


class TestFactPreconditionError(TestCase):
    """Phase-aware handling of FactPreconditionError via check_preconditions() in get_fact()."""

    def test_prepare_phase_returns_default(self):
        """Precondition not satisfied during prepare → fact returns default() silently."""
        state = _make_state(is_executing=False)
        host = MagicMock()

        with patch(
            "pyinfra.api.facts._get_fact",
            side_effect=FactPreconditionError(ZfsPools, "zfs module not loaded"),
        ):
            result = get_fact(state, host, ZfsPools)

        assert result == ZfsPools().default()

    def test_execute_phase_raises(self):
        """Precondition not satisfied during execute → FactPreconditionError propagates."""
        state = _make_state(is_executing=True)
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


class _AsksAboutAProject(FactBase):
    """
    A fact whose precondition needs the argument the fact was asked about.

    It records what it received, because the fact instance is built inside `_get_fact` and the test
    cannot reach it.
    """

    default = dict
    seen: dict = {}

    def check_preconditions(self, state, host, **fact_kwargs):
        type(self).seen = fact_kwargs

    def command(self, project=None, remote=None):
        return "echo '[]'"

    def process(self, output):
        return {}


class _Parameterless(FactBase):
    """A fact written the old way, with a precondition that takes nothing."""

    default = str
    called = False

    def check_preconditions(self, state, host):
        type(self).called = True

    def command(self):
        return "echo ok"

    def process(self, output):
        return "ok"


class TestPreconditionReceivesFactArguments(TestCase):
    """
    `check_preconditions(self, state, host)` cannot serve a fact that takes parameters: it has no
    way to tell which project or pool it is being asked about. The fact's own arguments are handed
    to it, named as its `command` declares them.
    """

    def _run(self, fact_cls, fact_kwargs):
        state = _make_state(is_executing=False)
        host = MagicMock()
        host.connected = True
        host.run_shell_command.return_value = (True, CommandOutput([OutputLine("stdout", "[]")]))

        with patch("pyinfra.api.facts._handle_fact_kwargs", return_value=(fact_kwargs, {})):
            return get_fact(state, host, fact_cls)

    def test_a_fact_is_told_which_arguments_it_was_asked_about(self):
        _AsksAboutAProject.seen = {}
        self._run(
            _AsksAboutAProject,
            {"self": _AsksAboutAProject(), "project": "runboat", "remote": None},
        )

        # `self` is in there too — that is what getcallargs collects — and passing it through would
        # be a TypeError, so its absence is half of what this asserts.
        assert _AsksAboutAProject.seen == {"project": "runboat", "remote": None}

    def test_a_fact_without_parameters_is_called_the_same_way(self):
        _Parameterless.called = False
        self._run(_Parameterless, {"self": _Parameterless()})

        assert _Parameterless.called is True
