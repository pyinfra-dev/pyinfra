#!/usr/bin/env python

from inspect import getfullargspec
from os import makedirs, path

from docs.utils import title_line
from pyinfra.api.connectors import get_all_connectors


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

        if connector.__doc__:
            lines.append(connector.__doc__)

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
.. code:: python

    pyinfra @{connector_name}{names_argument_key} ...
""".strip(),
        )
        lines.append("")

        data_keys = connector.Meta.DataKeys.__dict__

        data_key_lines = []
        for key, description in data_keys.items():
            if key.startswith("_"):
                continue
            data_key_lines.append(f"    {connector.Meta.keys_prefix}_{key}  # {description}")

        if data_key_lines:
            data_title = "Available Data"
            lines.append(data_title)
            lines.append(title_line("~", data_title))
            lines.append("")

            data_key_lines = "\n".join(data_key_lines)
            lines.append(
                f"""
.. code:: python

{data_key_lines}
    """.strip(),
            )
            lines.append("")

        module_filename = path.join(docs_dir, "connectors", f"{connector_name}.rst")
        print("--> Writing {0}".format(module_filename))

        with open(module_filename, "w") as outfile:
            outfile.write("\n".join(lines))


if __name__ == "__main__":
    print("### Building connectors docs")
    build_connectors_docs()
