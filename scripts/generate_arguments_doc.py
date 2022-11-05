#!/usr/bin/env python

from os import path

from pyinfra.api import Config
from pyinfra.api.arguments import OPERATION_KWARG_DOC


def build_arguments_doc():
    pyinfra_config = Config()

    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))

    lines = []

    for category, note, kwarg_configs in OPERATION_KWARG_DOC:
        lines.append("\n{0}".format(category))
        lines.append("".join("~" for _ in range(len(category))))
        lines.append("")

        if note:
            note_block = f"""
.. note::
    {note}
"""
            lines.append(note_block)

        for key, config in kwarg_configs.items():
            description = config
            if isinstance(config, dict):
                description = config.get("description")
                default = config.get("default")
                if callable(default):
                    default = default(pyinfra_config)
                if default is not None:
                    key = "{0}={1}".format(key, default)

            block = f"""
.. compound::
    ``{key}``
        {description}
"""

            lines.append(block)

    module_filename = path.join(docs_dir, "_deploy_globals.rst")
    print("--> Writing {0}".format(module_filename))

    out = "\n".join(lines)

    with open(module_filename, "w", encoding="utf-8") as outfile:
        outfile.write(out)


if __name__ == "__main__":
    print("### Building arguments doc")
    build_arguments_doc()
