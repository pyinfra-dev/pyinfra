#!/usr/bin/env python

import inspect
import pkgutil
import sys
from importlib import import_module

import pyinfra.operations
from pyinfra.api.arguments import all_argument_meta


def main() -> int:
    global_names = set(all_argument_meta)
    errors: list[str] = []

    for module_info in pkgutil.walk_packages(pyinfra.operations.__path__, "pyinfra.operations."):
        module = import_module(module_info.name)

        for operation_name, operation in vars(module).items():
            inner = getattr(operation, "_inner", None)
            if inner is None or not callable(inner):
                continue

            collisions = global_names.intersection(inspect.signature(inner).parameters)
            for name in sorted(collisions):
                errors.append(
                    f"{module_info.name}.{operation_name}: "
                    f"'{name}' shadows a global operation argument",
                )

    if errors:
        print("Operation argument collisions found:")
        for error in errors:
            print(f"  {error}")
        return 1

    print("No operation argument collisions found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
