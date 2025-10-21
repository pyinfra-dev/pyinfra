#!/usr/bin/env python

import sys
from glob import glob
from importlib import import_module
from inspect import getfullargspec, getmembers, isclass
from os import makedirs, path
from types import FunctionType

from pyinfra.api.facts import FactBase

sys.path.append(".")
from docs.utils import format_doc_line, title_line  # noqa: E402

MODULE_DEF_LINE_MAX = 90


def build_operations_docs():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))
    operations_dir = path.join(this_dir, "..", "src", "pyinfra", "operations", "*.py")

    makedirs(path.join(docs_dir, "operations"), exist_ok=True)

    op_module_names = [
        path.basename(name)[:-3]
        for name in glob(operations_dir)
        if not name.endswith("__init__.py")
    ]

    for module_name in op_module_names:
        lines = []

        print("--> Doing module: {0}".format(module_name))
        module = import_module("pyinfra.operations.{0}".format(module_name))

        full_title = "{0} Operations".format(module_name.title())
        lines.append(full_title)
        lines.append(title_line("-", full_title))
        lines.append("")

        if module.__doc__:
            lines.append(module.__doc__)

        operation_facts = [
            (key, value)
            for key, value in getmembers(module)
            if (isclass(value) and issubclass(value, FactBase))
        ]

        if operation_facts:
            lines.append("")

            items = []
            for key, value in operation_facts:
                fact_module = value.__module__.replace("pyinfra.facts.", "")
                items.append(f":ref:`facts:{fact_module}.{key}`")

            lines.append("Facts used in these operations: {0}.".format(", ".join(items)))
            lines.append("")

        operation_functions = [
            (key, value._inner)
            for key, value in getmembers(module)
            if (
                isinstance(value, FunctionType)
                and value.__module__ == module.__name__
                and getattr(value, "_inner", False)
                and not value.__name__.startswith("_")
                and not key.startswith("_")
            )
        ]

        for name, func in operation_functions:
            decorated_func = getattr(func, "_inner", None)
            while decorated_func:
                func = decorated_func
                decorated_func = getattr(func, "_inner", None)

            lines.append(".. _operations:{0}.{1}:".format(module_name, name))
            lines.append("")

            title_name = ":code:`{0}.{1}`".format(module_name, name)
            lines.append(title_name)

            # Underline name with -'s for title
            lines.append(title_line("~", title_name))

            if getattr(func, "is_idempotent", None) is False:
                text = (
                    getattr(func, "idempotent_notice", None)
                    or "This operation will always execute commands and is not idempotent."
                )
                lines.append(
                    """
.. admonition:: Stateless operation
    :class: important

    {0}
""".format(
                        text,
                    ),
                )

            doc = func.__doc__
            if doc:
                docbits = doc.strip().split("\n")
                description_lines = []

                for line in docbits:
                    if line:
                        description_lines.append(line)
                    else:
                        break

                if len(docbits) > 0:
                    lines.append("")
                    lines.extend([line.strip() for line in description_lines])
                    lines.append("")
                    doc = "\n".join(docbits[len(description_lines) :])

            argspec = getfullargspec(func)

            # Make default strings appear as strings
            arg_defaults = (
                ['"{}"'.format(arg) if isinstance(arg, str) else arg for arg in argspec.defaults]
                if argspec.defaults
                else None
            )

            # Create a dict of arg name -> default
            defaults = (
                dict(
                    zip(
                        argspec.args[-len(arg_defaults) :],
                        arg_defaults,
                    ),
                )
                if arg_defaults
                else {}
            )

            # Build args string
            args = []

            for arg in argspec.args:
                if arg in ("state", "host") or arg.startswith("_"):
                    continue

                value = arg

                if arg in argspec.annotations:
                    value += f": {argspec.annotations[arg]}"

                if arg in defaults:
                    value += f"={defaults[arg]}"

                args.append(value)

            # Add **kwargs to indicate global arguments
            args.append("**kwargs")

            if len(", ".join(args)) <= MODULE_DEF_LINE_MAX:
                args_string = ", ".join(args)

            else:
                arg_buffer = []
                arg_lines = []
                for arg in args:
                    if len(", ".join(arg_buffer + [arg])) >= MODULE_DEF_LINE_MAX:
                        arg_lines.append(arg_buffer)
                        arg_buffer = []

                    arg_buffer.append(arg)

                if arg_buffer:
                    arg_lines.append(arg_buffer)

                arg_lines = ["        {0}".format(", ".join(line_args)) for line_args in arg_lines]

                args_string = "\n{0},\n    ".format(",\n".join(arg_lines))

            # Attach the code block
            lines.append(
                """
.. code:: python

    {0}.{1}({2})

""".strip().format(
                    module_name,
                    name,
                    args_string,
                ),
            )

            # Append any remaining docstring
            if doc:
                lines.append("")
                lines.append(
                    "{0}".format(
                        "\n".join([format_doc_line(line) for line in doc.split("\n")]),
                    ).strip(),
                )

            lines.append(
                "Note:\n\tThis operation also inherits all :doc:`global arguments </arguments>`."
            )
            lines.append("")
            lines.append("")

        # Write out the file
        module_filename = path.join(docs_dir, "operations", "{0}.rst".format(module_name))
        print("--> Writing {0}".format(module_filename))

        with open(module_filename, "w", encoding="utf-8") as outfile:
            outfile.write("\n".join(lines))


if __name__ == "__main__":
    print("### Building operations docs")
    build_operations_docs()
