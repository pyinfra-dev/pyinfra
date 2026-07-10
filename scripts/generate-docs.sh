#!/bin/bash
# Run all the documentation generators that introspect pyinfra's source and
# emit Markdown pages + card snippets into docs/. Must run before `zensical
# build` — zensical has no build-time hooks.

source "$(dirname "$0")/common.bash"    # setup $uvrun, etc.

cd "$(dirname "$0")/.."

echo "### Cleaning generated docs (preserving hand-written index.md files)"
mkdir -p docs/operations docs/facts docs/connectors snippets
find docs/operations docs/facts docs/connectors -maxdepth 1 -type f -name '*.md' ! -name 'index.md' -delete

echo "### Generating operations docs"
$uvrun python scripts/generate_operations_docs.py

echo "### Generating facts docs"
$uvrun python scripts/generate_facts_docs.py

echo "### Generating connectors docs"
$uvrun python scripts/generate_connectors_docs.py

echo "### Generating arguments snippet"
$uvrun python scripts/generate_arguments_doc.py

echo "### Generating llms.txt"
$uvrun python scripts/generate_llms_txt.py
