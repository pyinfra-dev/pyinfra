#!/usr/bin/env python

import sys
from importlib import import_module
from inspect import getfullargspec, getmembers, isclass
from os import makedirs, path
from pathlib import Path
from types import FunctionType, MethodType

from pyinfra.api.facts import FactBase, ShortFactBase

sys.path.append(".")
from docs.utils import (
    format_doc_line,
    title_line,
    including_sub_modules,
    get_module_names,
    remove_dups,
)  # noqa: E402


def build_facts_docs():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))
    pyinfra_dir = Path(docs_dir).parent / "src" / "pyinfra"

    makedirs(path.join(docs_dir, "facts"), exist_ok=True)

    for module_name in sorted(get_module_names(pyinfra_dir / "facts")):
        lines = []
        print("--> Doing fact module: {0}".format(module_name))
        module = import_module("pyinfra.facts.{0}".format(module_name))

        full_title = "{0} Facts".format(module_name.title())
        lines.append(full_title)
        lines.append(title_line("-", full_title))
        lines.append("")

        if module.__doc__:
            lines.append(module.__doc__)

        ops_paths = {
            pyinfra_dir / "operations" / name for name in [module_name, f"{module_name}.py"]
        }
        if any(p.exists() for p in ops_paths):
            lines.append(f"See also: :doc:`../operations/{module_name}`.")
            lines.append("")

        all_fact_classes = [
            (key, value)
            for m in including_sub_modules(module)
            for key, value in getmembers(m)
            if (
                isclass(value)
                and (issubclass(value, FactBase) or issubclass(value, ShortFactBase))
                and value.__module__.startswith(m.__name__)
                and value is not FactBase
                and not value.__name__.endswith("Base")  # hacky!
            )
        ]

        fact_classes = remove_dups(all_fact_classes)
        for fact, cls in fact_classes:
            # FactClass -> fact_accessor on host object
            name = fact
            args_string_and_brackets = ""

            # Does this fact take args?
            command_attr = getattr(cls, "command", None)
            if isinstance(command_attr, (FunctionType, MethodType)):
                # Attach basic argspec to name
                # Note only supports facts with one arg as this is all that's
                # possible, will need to refactor to print properly in future.
                argspec = getfullargspec(command_attr)

                arg_defaults = (
                    [
                        "'{}'".format(arg) if isinstance(arg, str) else arg
                        for arg in argspec.defaults
                    ]
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

                if len(argspec.args) and (argspec.args != ["self"]):
                    args_string_and_brackets = ", {0}".format(
                        ", ".join(
                            ("{0}={1}".format(arg, defaults.get(arg)) if arg in defaults else arg)
                            for arg in argspec.args
                            if arg != "self"
                        ),
                    )

            lines.append(".. _facts:{0}.{1}:".format(module_name, name))
            # Modules that re-export classes under an alias (e.g. facts/zfs.py
            # exposes both ZfsDatasets and Datasets pointing at the same class)
            # end up keyed by whichever name getmembers sees first. Emit the
            # canonical class name as an extra label so cross-refs from the
            # operations docs resolve regardless of import style.
            if cls.__name__ != name:
                lines.append(".. _facts:{0}.{1}:".format(module_name, cls.__name__))
            lines.append("")

            title = ":code:`{0}.{1}`".format(module_name, name)
            lines.append(title)

            # Underline name with -'s for title
            lines.append(title_line("~", title))
            lines.append("")

            # Attach the code block
            lines.append(
                """
.. code:: python

    host.get_fact({1}{2})

""".strip().format(
                    module_name,
                    name,
                    args_string_and_brackets,
                ),
            )

            # Append any docstring
            doc = cls.__doc__
            if doc:
                lines.append("")
                lines.append(
                    "{0}".format(
                        "\n".join([format_doc_line(line) for line in doc.split("\n")]),
                    ).strip(),
                )

            lines.append("")
            lines.append("")

        # Write out the file
        module_filename = path.join(docs_dir, "facts", "{0}.rst".format(module_name))
        print("--> Writing {0}".format(module_filename))

        with open(module_filename, "w", encoding="utf-8") as outfile:
            outfile.write("\n".join(lines))


if __name__ == "__main__":
    print("### Building fact docs")
    build_facts_docs()
