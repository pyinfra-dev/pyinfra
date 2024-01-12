#!/usr/bin/env python

import sys
from inspect import cleandoc, getdoc, getfullargspec
from os import makedirs, path
from typing import get_type_hints

from pyinfra.api.connectors import get_all_connectors

sys.path.append(".")
from docs.utils import title_line  # noqa: E402


def build_connectors_docs():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))

    makedirs(path.join(docs_dir, "connectors"), exist_ok=True)

    for connector_name, connector in get_all_connectors().items():
        lines = []

        full_title = "``@{0}`` Connector".format(connector_name)
        lines.append(full_title)
        lines.append(title_line("-", full_title))
        lines.append("")

        doc = getdoc(connector)
        if doc:
            lines.append(doc)
            lines.append("")

        data_title = "Usage"
        lines.append(data_title)
        lines.append(title_line("~", data_title))
        lines.append("")

        names_argument_key = getfullargspec(connector.make_names_data).args[0]
        if names_argument_key == "_":
            names_argument_key = ""
        else:
            names_argument_key = f"/{names_argument_key}"
        lines.append(
            f"""
.. code:: shell

    pyinfra @{connector_name}{names_argument_key} ...
""".strip(),
        )
        lines.append("")

        data_key_lines = []

        for key, type_ in get_type_hints(connector.data_cls).items():
            if key.startswith("_"):
                continue
            meta = connector.data_meta[key]
            default = "" if meta.default is None else f"``{meta.default}``"
            data_key_lines.append(
                f"""   * - ``{key}``
     - {meta.description}
     - ``{type_.__name__}``
     - {default}
"""
            )
        if data_key_lines:
            data_title = "Available Data"
            lines.append(data_title)
            lines.append(title_line("~", data_title))
            lines.append("")
            lines.append(
                "The following keys can be set as host or group data to control "
                "how this connector interacts with the target."
            )
            lines.append("")

            data_key_lines = "\n".join(data_key_lines)
            lines.append(
                f"""
.. list-table::
   :header-rows: 1
   :widths: 25 45 15 15

   * - Key
     - Description
     - Type
     - Default
{data_key_lines}
    """.strip(),
            )
            lines.append("")

        examples_doc = getattr(connector, "__examples_doc__", None)
        if examples_doc:
            lines.append("Examples")
            lines.append(title_line("~", "Examples"))
            lines.append("")
            lines.append(cleandoc(examples_doc))

        module_filename = path.join(docs_dir, "connectors", f"{connector_name}.rst")
        print("--> Writing {0}".format(module_filename))

        with open(module_filename, "w", encoding="utf-8") as outfile:
            outfile.write("\n".join(lines))


if __name__ == "__main__":
    print("### Building connectors docs")
    build_connectors_docs()
