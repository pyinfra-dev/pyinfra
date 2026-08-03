#!/usr/bin/env python

import sys
from os import makedirs, path
from typing import get_type_hints

from pyinfra.api import Config
from pyinfra.api.arguments import AllArguments, __argument_docs__
from pyinfra.api.host import Host
from pyinfra.api.operation import OperationMeta

sys.path.append(path.dirname(path.realpath(__file__)))
from docs_utils import prepare_docstring  # noqa: E402


def build_arguments_doc():
    pyinfra_config = Config()

    this_dir = path.dirname(path.realpath(__file__))
    snippets_dir = path.abspath(path.join(this_dir, "..", "snippets"))
    makedirs(snippets_dir, exist_ok=True)

    lines = []

    # Extend locals with hidden (behind TYPE_CHECKING) imports in the arguments
    # module so get_type_hints can resolve them.
    locals_ = locals()
    locals_["Host"] = Host
    locals_["OperationMeta"] = OperationMeta

    all_arguments = get_type_hints(AllArguments)

    for group_name, (
        arguments_meta,
        arguments_title_doc,
        arguments_example_doc,
    ) in __argument_docs__.items():
        slug = group_name.lower().replace(" & ", "-").replace(" ", "-")

        lines.append(f"## {group_name} {{ #{slug} }}")
        lines.append("")

        if arguments_title_doc:
            lines.append(prepare_docstring(arguments_title_doc))
            lines.append("")

        lines.append("| Key | Description | Type | Default |")
        lines.append("| --- | --- | --- | --- |")

        for key, meta in arguments_meta.items():
            default = meta.default
            if callable(default):
                default = default(pyinfra_config)
            default = "" if default is None else f"`{default}`"

            type_ = all_arguments[key]
            type_name = type_.__name__
            if hasattr(type_, "__args__"):
                type_args = ", ".join([arg.__name__ for arg in type_.__args__])
                type_name = f"{type_name}[{type_args}]"

            description = (meta.description or "").replace("\n", " ").strip()
            lines.append(f"| `{key}` | {description} | `{type_name}` | {default} |")

        lines.append("")

        if arguments_example_doc:
            lines.append("**Examples:**")
            lines.append("")
            lines.append(prepare_docstring(arguments_example_doc))
            lines.append("")

    out_filename = path.join(snippets_dir, "deploy-globals.md")
    print(f"--> Writing {out_filename}")

    with open(out_filename, "w", encoding="utf-8") as outfile:
        outfile.write("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    print("### Building arguments doc")
    build_arguments_doc()
