from unittest import TestCase
from unittest.mock import patch

from pyinfra.api import Config
from pyinfra.api.exceptions import PyinfraError


class TestStateApi(TestCase):
    def test_require_pyinfra_requirement_ok(self):
        with patch("pyinfra.api.config.__version__", "100"):
            Config(REQUIRE_PYINFRA_VERSION=">=100")

    def test_require_pyinfra_requirement_too_low(self):
        with self.assertRaises(PyinfraError) as context:
            with patch("pyinfra.api.config.__version__", "99"):
                Config(REQUIRE_PYINFRA_VERSION=">=100")

        assert context.exception.args[0] == (
            "pyinfra version requirement not met (requires >=100, running 99)"
        )
