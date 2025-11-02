#!/usr/bin/env python

from os import path, remove

from pyinfra import local


def generate_api_docs():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))
    pyinfra_dir = path.abspath(path.join(this_dir, "..", "src", "pyinfra"))

    api_doc_command = (
        "uv run sphinx-apidoc -e -M -f -o {0}/apidoc/ {1} {1}/facts {1}/operations {1}/connectors"
    ).format(
        docs_dir,
        pyinfra_dir,
    )

    local.shell(
        (api_doc_command,),
        print_input=True,
    )

    for filename in ("modules.rst", "pyinfra.rst", "pyinfra.api.rst"):
        remove("{0}/apidoc/{1}".format(docs_dir, filename))


if __name__ == "__main__":
    print("### Generating API docs")
    generate_api_docs()
