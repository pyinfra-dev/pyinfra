from unittest import TestCase

from mock import patch

from pyinfra.api import Config, State
from pyinfra.api.exceptions import PyinfraError

from ..util import make_inventory


class TestStateApi(TestCase):
    def test_require_pyinfra_requirement_ok(self):
        config = Config(REQUIRE_PYINFRA_VERSION='>=100')
        inventory = make_inventory()

        with patch('pyinfra.api.state.__version__', '100'):
            State(inventory, config)

    def test_require_pyinfra_requirement_too_low(self):
        config = Config(REQUIRE_PYINFRA_VERSION='>=100')
        inventory = make_inventory()

        with self.assertRaises(PyinfraError) as context:
            with patch('pyinfra.api.state.__version__', '99'):
                State(inventory, config)

        assert context.exception.args[0] == (
            'pyinfra version requirement not met (requires >=100, running 99)'
        )

    def test_require_pyinfra_min_version_ok(self):
        config = Config(MIN_PYINFRA_VERSION=100)
        inventory = make_inventory()

        with patch('pyinfra.api.state.__version__', '100'):
            State(inventory, config)

    def test_pyinfra_min_version_ignored_when_required_version_set(self):
        config = Config(
            REQUIRE_PYINFRA_VERSION='==100',
            MIN_PYINFRA_VERSION=1000,  # should be ignored
        )
        inventory = make_inventory()

        with patch('pyinfra.api.state.__version__', '100'):
            State(inventory, config)
