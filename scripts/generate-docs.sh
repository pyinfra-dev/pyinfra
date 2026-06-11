#!/bin/bash
# Run all the documentation generators that introspect pyinfra's source and
# emit Markdown pages + card snippets into docs/. Must run before `zensical
# build` — zensical has no build-time hooks.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "### Cleaning generated docs (preserving hand-written index.md files)"
mkdir -p docs/operations docs/facts docs/connectors snippets
find docs/operations docs/facts docs/connectors -maxdepth 1 -type f -name '*.md' ! -name 'index.md' -delete

echo "### Generating operations docs"
uv run python scripts/generate_operations_docs.py

echo "### Generating facts docs"
uv run python scripts/generate_facts_docs.py

echo "### Generating connectors docs"
uv run python scripts/generate_connectors_docs.py

echo "### Generating arguments snippet"
uv run python scripts/generate_arguments_doc.py
