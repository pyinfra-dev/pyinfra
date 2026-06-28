#!/usr/bin/env python

import sys
from inspect import getfullargspec
from os import makedirs, path
from typing import get_type_hints

from pyinfra.api.connectors import get_all_connectors

sys.path.append(path.dirname(path.realpath(__file__)))
from docs_utils import prepare_docstring  # noqa: E402


def build_connectors_docs():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))

    makedirs(path.join(docs_dir, "connectors"), exist_ok=True)

    for connector_name, connector in get_all_connectors().items():
        lines = [
            "---",
            "template: connector.html",
            "---",
            "",
        ]

        lines.append(f"# `@{connector_name}` Connector")
        lines.append("")

        doc = prepare_docstring(connector.__doc__)
        if doc:
            lines.append(doc)
            lines.append("")

        examples_doc = getattr(connector, "__examples_doc__", None)
        if examples_doc:
            lines.append("## Examples")
            lines.append("")
            lines.append(prepare_docstring(examples_doc))
            lines.append("")
        else:
            lines.append("## Examples")
            lines.append("")
            names_argument_key = getfullargspec(connector.make_names_data).args[0]
            if names_argument_key == "_":
                names_argument_key = ""
            else:
                names_argument_key = f"/{names_argument_key}"
            lines.append("```shell")
            lines.append(f"pyinfra @{connector_name}{names_argument_key} ...")
            lines.append("```")
            lines.append("")

        data_rows = []
        for key, type_ in get_type_hints(connector.data_cls).items():
            if key.startswith("_"):
                continue
            meta = connector.data_meta[key]
            default = "" if meta.default is None else f"`{meta.default}`"
            description = (meta.description or "").replace("\n", " ").strip()
            data_rows.append(f"| `{key}` | {description} | `{type_.__name__}` | {default} |")

        if data_rows:
            lines.append("## Available Data")
            lines.append("")
            lines.append(
                "The following keys can be set as host or group data to control "
                "how this connector interacts with the target."
            )
            lines.append("")
            lines.append("| Key | Description | Type | Default |")
            lines.append("| --- | --- | --- | --- |")
            lines.extend(data_rows)
            lines.append("")

        module_filename = path.join(docs_dir, "connectors", f"{connector_name}.md")
        print(f"--> Writing {module_filename}")

        with open(module_filename, "w", encoding="utf-8") as outfile:
            outfile.write("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    print("### Building connectors docs")
    build_connectors_docs()
