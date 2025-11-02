#!/bin/bash

set -euo pipefail

NEXT_BRANCH="3.x"
LATEST_BRANCH="3.x"

BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
TAG_NAME=$(git tag --points-at HEAD)

echo "branch=${BRANCH_NAME}"
echo "tag=${TAG_NAME:-<none>}"

build_docs() {
    local docs_version=$1
    local build_dir=$2

    echo "Building docs for version: ${docs_version}"
    rm -rf "$build_dir"
    DOCS_VERSION=$docs_version uv run sphinx-build -a docs/ "$build_dir"
}

copy_docs() {
    local build_dir=$1
    local output_dir=$2

    mkdir -p "$output_dir"
    cp -r "$build_dir"/* "$output_dir/"
}

# Build "next" docs
if [ "${BRANCH_NAME}" = "${NEXT_BRANCH}" ]; then
    build_docs "next" "build/docs"
    copy_docs "build/docs" "docs/public/en/next"
fi

# Build "latest" docs
if [ "${BRANCH_NAME}" = "${LATEST_BRANCH}" ]; then
    build_docs "latest" "build/docs"
    copy_docs "build/docs" "docs/public/en/latest"
fi

# Build versioned docs for a valid tag
if [ -n "${TAG_NAME}" ] && [[ "$TAG_NAME" =~ ^v[0-9]+\.[0-9]+([\.a-z0-9]+)?$ ]]; then
    build_docs "$BRANCH_NAME" "build/docs"
    copy_docs "build/docs" "docs/public/en/${BRANCH_NAME}"

    if [ "${BRANCH_NAME}" = "${LATEST_BRANCH}" ]; then
        echo "Generating /page redirects"
        DOCS_VERSION=$BRANCH_NAME uv run python scripts/generate_redirect_pages.py
    fi
fi

# Local build only to build/docs
if [[ -z "${TAG_NAME}" ]] && [[ "${BRANCH_NAME}" != "${LATEST_BRANCH}" && "${BRANCH_NAME}" != "${NEXT_BRANCH}" ]]; then
    echo "Performing local build for branch: ${BRANCH_NAME}"
    build_docs "$BRANCH_NAME" "build/docs"
    echo "Docs built to build/docs/"
    echo "You can open build/docs/index.html or run:"
    echo " python3 -m http.server -d build/docs"
fi
