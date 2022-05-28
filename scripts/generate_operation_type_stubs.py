"""
Generate type stubs for operations.

This is neccesary because ParamSpec and Concatenate does not support keyword args yet.
See https://github.com/Fizzadar/pyinfra/issues/476 for more info and
especially https://github.com/Fizzadar/pyinfra/issues/476#issuecomment-1100748320.

See any stub pyinfra/operations/*.pyi to see an example.

"""

import os
from logging import getLogger

import black
from redbaron import RedBaron

from pyinfra.api.arguments import OPERATION_KWARGS

logger = getLogger()


def _get_global_arg_names():
    """This extracts the argument names and types from the OPERATION_KWARGS global
    variable and generates a list of string on the form "{key}: {type} = None"."""
    args = []
    for arg_group in OPERATION_KWARGS.values():
        for arg_name, arg_config in arg_group.items():
            type_ = arg_config["type"]
            if type(type_) == type:
                # types like int' string representation is <class 'str'> so we extract the name
                type_ = type_.__name__
            args.append(f"{arg_name}: typing.Optional[{type_}] = None\n")
    return args


def create_operation_stub(file_path: str):
    """Given filepath, generates a stub file at if any function in that file is decorated with the
    @operation decorator.

    The decorator is only identified by name - we do not ensure that it is the specific decorator.
    Any decorator called "operation" would trigger a stub generation.
    """
    with open(file_path) as f:
        content = f.read()
    red = RedBaron(content)
    operations = red(
        "funcdef",  # get all function definitions
        lambda node: any(
            [dec("name", "operation") for dec in node.decorators],
        ),  # with decorator named "operation"
    )
    if operations:
        tree = RedBaron("import typing \n")
        global_args = _get_global_arg_names()
        ellipses = RedBaron("...")
        for operation in operations:
            stub = operation.copy()
            stub.decorators = []
            stub = stub.copy()
            stub.value = ellipses
            stub.arguments.extend(global_args)
            # *args and **kwargs must be moved the end of the argument list
            list_argument_index = None
            for i, argument in enumerate(stub.arguments):
                if argument.type == "list_argument":
                    list_argument_index = i
            if list_argument_index is not None:
                list_arg = stub.arguments[list_argument_index]
                stub.arguments.pop(
                    list_argument_index,
                )  # pop does not return the element for some reason
                stub.arguments.append(list_arg)

            dict_argument_index = None
            for i, argument in enumerate(stub.arguments):
                if argument.type == "dict_argument":
                    dict_argument_index = i
            if dict_argument_index is not None:
                dict_arg = stub.arguments[dict_argument_index]
                stub.arguments.pop(dict_argument_index)
                stub.arguments.append(dict_arg)
            tree.extend(RedBaron("\n\n"))
            tree.extend(stub)

        output_file_path = file_path + "i"

        pyi_content = tree.dumps() + "\n\n"
        # If using @operation(...) as opposed to @operation, it will generate a single long
        # for each function. Formatting with black solves this.
        pyi_content_formatted = black.format_str(pyi_content, mode=black.FileMode())

        with open(output_file_path, "w") as f:
            f.write(pyi_content_formatted)

    else:
        logger.info(f"No operations found in file {file_path}")


def create_all_operation_stubs():
    """Created stub for all files in pyinfra/operations (not recursively).
    Assume to be run from project root"""
    operation_dir = os.path.join("pyinfra", "operations")
    for operation_file in os.listdir(operation_dir):
        full_path = os.path.join(operation_dir, operation_file)
        if os.path.isfile(full_path) and os.path.splitext(full_path)[1] == ".py":
            logger.info(f"generate for file {full_path}")
            create_operation_stub(full_path)


if __name__ == "__main__":
    create_all_operation_stubs()
