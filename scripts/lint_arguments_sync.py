#!/usr/bin/env python
"""
Lint script to verify that arguments in arguments.py and arguments_typed.py are in sync.

Due to Python's typing limitations (ParamSpec args cannot be concatenated), we maintain
two separate definitions of global arguments:
- arguments.py: TypedDicts (ConnectorArguments, MetaArguments, ExecutionArguments)
- arguments_typed.py: PyinfraOperation.__call__ method signature

This script ensures they stay synchronized.
"""

import ast
import sys
from os import path
from typing import NamedTuple


class ArgumentInfo(NamedTuple):
    name: str
    type_annotation: str
    has_default: bool


def get_typeddict_keys(tree: ast.Module, class_names: list[str]) -> dict[str, str]:
    """Extract keys and their type annotations from TypedDict classes."""
    keys: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in class_names:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    key = item.target.id
                    type_str = ast.unparse(item.annotation)
                    keys[key] = type_str

    return keys


def get_argument_meta_keys(tree: ast.Module) -> set[str]:
    """Extract keys from all *_argument_meta dictionaries."""
    keys: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_argument_meta"):
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                keys.add(key.value)

    return keys


def get_call_parameters(tree: ast.Module, class_name: str, method_name: str) -> list[ArgumentInfo]:
    """Extract parameters from a class method."""
    params: list[ArgumentInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    args = item.args

                    # Count defaults - they align with the end of the args list
                    num_defaults = len(args.defaults)
                    num_args = len(args.args)

                    for i, arg in enumerate(args.args):
                        if arg.arg == "self":
                            continue

                        type_str = ast.unparse(arg.annotation) if arg.annotation else ""

                        # Check if this arg has a default
                        default_index = i - (num_args - num_defaults)
                        has_default = default_index >= 0

                        params.append(
                            ArgumentInfo(
                                name=arg.arg,
                                type_annotation=type_str,
                                has_default=has_default,
                            )
                        )

                    # Also check kwonly args
                    for i, arg in enumerate(args.kwonlyargs):
                        type_str = ast.unparse(arg.annotation) if arg.annotation else ""
                        has_default = args.kw_defaults[i] is not None
                        params.append(
                            ArgumentInfo(
                                name=arg.arg,
                                type_annotation=type_str,
                                has_default=has_default,
                            )
                        )

    return params


def normalize_type(type_str: str) -> str:
    """Normalize type string for comparison (handle Optional, Union, etc.)."""
    # Remove whitespace
    type_str = type_str.replace(" ", "")

    # Sort Union members for consistent comparison
    if type_str.startswith("Union[") or type_str.startswith("Optional["):
        # This is a simplified normalization - just for basic comparison
        pass

    return type_str


def main() -> int:
    this_dir = path.dirname(path.realpath(__file__))
    repo_root = path.abspath(path.join(this_dir, ".."))

    arguments_path = path.join(repo_root, "src", "pyinfra", "api", "arguments.py")
    arguments_typed_path = path.join(repo_root, "src", "pyinfra", "api", "arguments_typed.py")

    # Parse both files
    with open(arguments_path, encoding="utf-8") as f:
        arguments_tree = ast.parse(f.read())

    with open(arguments_typed_path, encoding="utf-8") as f:
        arguments_typed_tree = ast.parse(f.read())

    # Extract TypedDict keys from arguments.py
    typeddict_classes = ["ConnectorArguments", "MetaArguments", "ExecutionArguments"]
    typeddict_keys = get_typeddict_keys(arguments_tree, typeddict_classes)

    # Extract argument meta keys (the actual source of truth for what arguments exist)
    meta_keys = get_argument_meta_keys(arguments_tree)

    # Extract PyinfraOperation.__call__ parameters from arguments_typed.py
    call_params = get_call_parameters(arguments_typed_tree, "PyinfraOperation", "__call__")
    call_param_names = {p.name for p in call_params}
    call_param_types = {p.name: p.type_annotation for p in call_params}

    errors: list[str] = []
    warnings: list[str] = []

    # Check that all TypedDict keys are in PyinfraOperation.__call__
    for key, type_str in typeddict_keys.items():
        if key not in call_param_names:
            errors.append(
                f"Argument '{key}' is in arguments.py TypedDicts but missing from "
                f"PyinfraOperation.__call__ in arguments_typed.py"
            )
        elif key in call_param_types:
            typed_type = normalize_type(call_param_types[key])
            expected_type = normalize_type(type_str)

            # TypedDict uses non-Optional types, but PyinfraOperation uses Optional
            # So we do a loose check - the base type should match
            # This is a simplified check that may need refinement
            if expected_type not in typed_type and typed_type not in expected_type:
                # Check if it's just an Optional wrapper difference
                if f"Optional[{expected_type}]" != typed_type and expected_type != typed_type:
                    warnings.append(
                        f"Type mismatch for '{key}': "
                        f"arguments.py has '{type_str}', "
                        f"arguments_typed.py has '{call_param_types[key]}'"
                    )

    # Check that all PyinfraOperation.__call__ params (except special ones) are in TypedDicts
    # Skip *args and **kwargs which are the P.args/P.kwargs for operation-specific args
    special_params = {"args", "kwargs"}
    for param in call_params:
        if param.name in special_params:
            continue
        if param.name not in typeddict_keys:
            errors.append(
                f"Parameter '{param.name}' is in PyinfraOperation.__call__ but missing from "
                f"TypedDicts in arguments.py"
            )

    # Check that all meta keys are represented
    all_typeddict_keys = set(typeddict_keys.keys())
    for key in meta_keys:
        if key not in all_typeddict_keys:
            errors.append(f"Argument '{key}' is in argument_meta dicts but missing from TypedDicts")

    # Report results
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
        print()

    if errors:
        print("Errors:")
        for error in errors:
            print(f"  ❌ {error}")
        print()
        print(f"Found {len(errors)} error(s) and {len(warnings)} warning(s)")
        return 1

    print("✅ arguments.py and arguments_typed.py are in sync!")
    if warnings:
        print(f"   ({len(warnings)} warning(s) - type annotations may differ slightly)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
