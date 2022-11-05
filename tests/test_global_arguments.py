from glob import glob
from importlib import import_module
from inspect import getmembers
from os import path
from types import FunctionType
from unittest import TestCase

try:
    from inspect import getfullargspec
except ImportError:
    from inspect import signature as getfullargspec

from pyinfra import operations
from pyinfra.api.arguments import ALL_ARGUMENTS


def _is_pyinfra_operation(module, key, value):
    return (
        isinstance(value, FunctionType)
        and value.__module__ == module.__name__
        and getattr(value, "_pyinfra_op", False)
        and not value.__name__.startswith("_")
        and not key.startswith("_")
    )


def iter_operations():
    module_filenames = glob(path.join(path.dirname(operations.__file__), "*.py"))

    for module_name in sorted(module_filenames):
        module = import_module(
            "pyinfra.operations.{0}".format(
                path.basename(module_name)[:-3],
            ),
        )

        for key, value in sorted(getmembers(module)):
            if _is_pyinfra_operation(module, key, value):
                yield module, value


class TestOperationGlobalArguments(TestCase):
    def test_operations_do_not_use_global_arguments(self):
        global_arg_keys = ALL_ARGUMENTS.keys()

        for op_module, op_func in iter_operations():
            argspec = getfullargspec(op_func._pyinfra_op)
            for arg in argspec.args:
                assert (
                    arg not in global_arg_keys
                ), "`{0}` argument found in {1}.{2} operation function".format(
                    arg,
                    op_module.__name__,
                    op_func.__name__,
                )
