#!/bin/bash

set -euo pipefail

LATEST_NAME="3.x"
CURRENT_NAME="2.x"

BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
TAG_NAME=$(git tag --points-at HEAD)

if [ "${BRANCH_NAME}" = "${LATEST_NAME}" ]; then
    echo "Building latest docs (${LATEST_NAME})"
    env DOCS_VERSION=latest sphinx-build -a docs/ docs/public/en/latest/
fi

if [ "${BRANCH_NAME}" = "${CURRENT_NAME}" ]; then
    if [ -n "${TAG_NAME}" ] && [[ "$TAG_NAME" =~ ^v3\.[0-9]+(\.[0-9]+)?$ ]]; then
        echo "Building ${BRANCH_NAME} docs for tag: ${TAG_NAME}"
        env DOCS_VERSION=$BRANCH_NAME sphinx-build -a docs/ docs/public/en/$BRANCH_NAME/
        echo "Generating /page redirects"
        env DOCS_VERSION=$DOCS_VERSION python scripts/generate_redirect_pages.py
    fi
fi

echo "Docs build complete"
