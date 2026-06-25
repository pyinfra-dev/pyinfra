from unittest import mock
import unittest

from pyinfra.api.facts import fact


class TestFactDecorator(unittest.TestCase):
    def test_fact_metadata(self):
        @fact()
        def basic_fact() -> str:
            """A simple test fact"""
            return "hello"

        assert basic_fact.abstract is False
        assert basic_fact.name == f"{self.__module__}.basic_fact"
        assert basic_fact.__doc__ == "A simple test fact"

    def test_default_default_is_None(self):
        @fact()
        def fact_without_default() -> str:
            return "hello"

        assert fact_without_default.default() is None

    def test_default_value(self):
        @fact(default_value="world")
        def fact_with_default() -> str:
            return "hello"

        assert fact_with_default.default() == "world"

    def test_function_is_called_with_host_and_state(self):
        fake_state = mock.MagicMock(name="fake_state")
        fake_host = mock.MagicMock(name="fake_host")

        @fact()
        def fact_with_host_and_state(host, state) -> str:
            assert host is fake_host
            assert state is fake_state
            return "hello"

        assert fact_with_host_and_state.get(state=fake_state, host=fake_host) == "hello"
        assert (
            fact_with_host_and_state.get(
                fake_state,
                fake_host,
            )
            == "hello"
        )
        with self.assertRaises(TypeError):
            fact_with_host_and_state.get(fake_state, fake_host, ["ignored_positional_arg"])
        with self.assertRaises(TypeError):
            fact_with_host_and_state.get(
                fake_state, fake_host, [], {"ignored_keyword_arg": "ignored_value"}
            )

    def test_function_is_passed_args(self):
        fake_state = mock.MagicMock(name="fake_state")
        fake_host = mock.MagicMock(name="fake_host")
        fake_arg = mock.MagicMock(name="fake_arg")

        @fact()
        def fact_with_positional_arg(test_arg) -> str:
            assert test_arg is fake_arg
            return "hello"

        assert fact_with_positional_arg.get(fake_state, fake_host, [fake_arg]) == "hello"
        with self.assertRaises(TypeError):
            assert (
                fact_with_positional_arg.get(
                    fake_state,
                    fake_host,
                )
                == "hello"
            )
        with self.assertRaises(TypeError):
            assert (
                fact_with_positional_arg.get(fake_state, fake_host, [fake_arg, fake_arg]) == "hello"
            )

    def test_function_is_passed_kwargs(self):
        fake_state = mock.MagicMock(name="fake_state")
        fake_host = mock.MagicMock(name="fake_host")
        fake_arg = mock.MagicMock(name="fake_arg")

        @fact()
        def fact_with_keyword_arg(*, test_arg) -> str:
            assert test_arg is fake_arg
            return "hello"

        assert (
            fact_with_keyword_arg.get(fake_state, fake_host, kwargs={"test_arg": fake_arg})
            == "hello"
        )
        with self.assertRaises(TypeError):
            assert (
                fact_with_keyword_arg.get(
                    fake_state,
                    fake_host,
                )
                == "hello"
            )
        with self.assertRaises(TypeError):
            assert (
                fact_with_keyword_arg.get(fake_state, fake_host, kwargs={"unknown_arg": fake_arg})
                == "hello"
            )
        with self.assertRaises(TypeError):
            assert (
                fact_with_keyword_arg.get(
                    fake_state, fake_host, kwargs={"test_arg": fake_arg, "unknown_arg": fake_arg}
                )
                == "hello"
            )

    def test_client_cannot_provide_state_or_host_arg(self):
        fake_state = mock.MagicMock(name="fake_state")
        fake_host = mock.MagicMock(name="fake_host")
        fake_arg = mock.MagicMock(name="fake_arg")

        @fact()
        def fact_with_state_and_host(state, host):
            assert state is fake_state
            assert host is fake_host

        with self.assertRaises(TypeError):
            fact_with_state_and_host.get(fake_state, fake_host, kwargs={"state": fake_arg})
        with self.assertRaises(TypeError):
            fact_with_state_and_host.get(fake_state, fake_host, kwargs={"host": fake_arg})
