#!/bin/bash

set -euo pipefail

BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
TAG_NAME=$(git tag --points-at HEAD)

if [ ! "${BRANCH_NAME}" = "2.x" ]; then
    2>&1 echo "Not on 2.x branch, bailing!"
    exit 1
fi

echo "Building latest docs (2.x branch HEAD)"
env DOCS_VERSION=latest sphinx-build -a docs/ docs/public/en/latest/

if [ -n "${TAG_NAME}" ] && [[ "$TAG_NAME" =~ ^2\.[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Building 2.x docs for tag: ${TAG_NAME}"
    env DOCS_VERSION=2.x spinx-build -a docs/ docs/public/en/2.x/
    echo "Generating /page redirects"
    env DOCS_VERSION=$DOCS_VERSION python scripts/generate_redirect_pages.py
fi

echo "Docs build complete"
