#!/bin/sh

# pyinfra
# File: scripts/build_docs.sh
# Desc: build the pyinfra docs


# Build the apidoc/*.rst docs
rm -f docs/apidoc/*.rst
sh scripts/generate_api_docs.sh

# Build the modules/*.rst docs
rm -f docs/modules/*.rst
python scripts/generate_modules_docs.py

# Build the facts.rst doc
rm -f docs/facts.rst
python scripts/generate_facts_doc.py

# Build the HTML docs
sphinx-build -a docs/ docs/build/
