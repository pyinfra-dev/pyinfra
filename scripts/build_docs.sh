#!/bin/sh

set -e

# Build the apidoc/*.rst docs
rm -f docs/apidoc/*.rst
sh scripts/generate_api_docs.sh

# Build the HTML docs
sphinx-build -a docs/ docs/build/
