#!/usr/bin/env python

import sys
from importlib import import_module
from inspect import getmembers, isclass, signature
from os import makedirs, path
from pathlib import Path
from types import FunctionType

from pyinfra.api.facts import FactBase

sys.path.append(".")
from docs.utils import (
    format_doc_line,
    get_module_names,
    including_sub_modules,
    remove_dups,
    title_line,
)  # noqa: E402

MODULE_DEF_LINE_MAX = 90


def build_operations_docs():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))
    pyinfra_dir = Path(docs_dir).parent / "src" / "pyinfra"

    makedirs(path.join(docs_dir, "operations"), exist_ok=True)

    for module_name in get_module_names(pyinfra_dir / "operations"):
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
            for m in including_sub_modules(module)
            for key, value in getmembers(m)
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

        all_operation_functions = [
            (f"{m.__name__.split('.')[-1]}.{key}" if m != module else key, value._inner)
            for m in including_sub_modules(module)
            for key, value in getmembers(m)
            if (
                isinstance(value, FunctionType)
                and value.__module__.startswith(m.__name__)
                and getattr(value, "_inner", False)
                and not value.__name__.startswith("_")
                and not key.startswith("_")
            )
        ]
        # remove duplicates in case functions imported by __init__.py and then also seen where defined
        operation_functions = remove_dups(all_operation_functions)

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

            # get signature, remove parens, append (or set) kwargs for global arguments and
            # expand spacing so params are indented wrt to the operation name
            args_string = signature(func).format(
                max_width=MODULE_DEF_LINE_MAX,
            )
            args_string = (
                f"{args_string[:-1].rstrip()},\n    **kwargs,\n"
                if args_string != "()"
                else "**kwargs,"
            )
            args_string = f"{args_string.replace('   ', '        ')}    )"

            # Attach the code block
            lines.append(
                """
.. code:: python

    {0}.{1}{2}

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

            lines.append("")
            lines.append(
                ".. note::\n    This operation also inherits all :doc:`global arguments </arguments>`."
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
