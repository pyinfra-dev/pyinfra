#!/bin/bash

set -euo pipefail

# Generates /en/next
NEXT_BRANCH="3.x"
# Generates /en/latest AND redirects /page -> /en/$NAME
LATEST_BRANCH="3.x"


BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
TAG_NAME=$(git tag --points-at HEAD)

echo "branch=${BRANCH_NAME}"
echo "tag=${TAG_NAME}"

if [ "${BRANCH_NAME}" = "${NEXT_BRANCH}" ]; then
    echo "Building next docs (${NEXT_BRANCH})"
    env DOCS_VERSION=next uv run sphinx-build -a docs/ docs/public/en/next/
fi

if [ "${BRANCH_NAME}" = "${LATEST_BRANCH}" ]; then
    echo "Building latest docs (${LATEST_BRANCH})"
    env DOCS_VERSION=latest uv run sphinx-build -a docs/ docs/public/en/latest/
fi

if [ -n "${TAG_NAME}" ] && [[ "$TAG_NAME" =~ ^v[0-9]\.[0-9]+([\.a-z0-9]+)?$ ]]; then
    echo "Building ${BRANCH_NAME} docs for tag: ${TAG_NAME}"
    env DOCS_VERSION=$BRANCH_NAME uv run sphinx-build -a docs/ docs/public/en/$BRANCH_NAME/

    if [ "${BRANCH_NAME}" = "${LATEST_BRANCH}" ]; then
        echo "Generating /page redirects"
        env DOCS_VERSION=$BRANCH_NAME uv run python scripts/generate_redirect_pages.py
    fi
fi

echo "Docs build complete"
