#!/usr/bin/env python

import sys
from inspect import cleandoc
from os import path
from typing import get_type_hints

from pyinfra.api import Config
from pyinfra.api.arguments import AllArguments, __argument_docs__
from pyinfra.api.host import Host
from pyinfra.api.operation import OperationMeta

sys.path.append(".")
from docs.utils import title_line  # noqa: E402


def build_arguments_doc():
    pyinfra_config = Config()

    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))

    lines = []

    # Extend locals with hidden (behind TYPE_CHECKING) imports in the arguments module
    locals_ = locals()
    locals_["Host"] = Host
    locals_["OperationMeta"] = OperationMeta

    all_arguments = get_type_hints(AllArguments)

    for group_name, (
        arguments_meta,
        arguments_title_doc,
        arguments_example_doc,
    ) in __argument_docs__.items():
        lines.append("\n{0}".format(group_name))
        lines.append(title_line("~", group_name))
        lines.append("")

        if arguments_title_doc:
            lines.append(cleandoc(arguments_title_doc))
            lines.append("")

        lines.append(
            """.. list-table::
   :header-rows: 1
   :widths: 25 45 15 15

   * - Key
     - Description
     - Type
     - Default"""
        )

        for key, meta in arguments_meta.items():
            default = meta.default
            if callable(default):
                default = default(pyinfra_config)
            default = "" if default is None else f"``{default}``"

            type_ = all_arguments[key]
            type_name = type_.__name__
            if hasattr(type_, "__args__"):
                type_args = ", ".join([arg.__name__ for arg in type_.__args__])
                type_name = f"{type_name}[{type_args}]"

            lines.append(
                f"""   * - ``{key}``
     - {meta.description}
     - ``{type_name}``
     - {default}
"""
            )

        if arguments_example_doc:
            lines.append("**Examples:**")
            lines.append("")
            lines.append(cleandoc(arguments_example_doc))

    module_filename = path.join(docs_dir, "_deploy_globals.rst")
    print("--> Writing {0}".format(module_filename))

    out = "\n".join(lines)

    with open(module_filename, "w", encoding="utf-8") as outfile:
        outfile.write(out)


if __name__ == "__main__":
    print("### Building arguments doc")
    build_arguments_doc()
