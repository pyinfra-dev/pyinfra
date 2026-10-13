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

    echo "Generating docs for version: ${docs_version}"
    scripts/generate-docs.sh

    echo "Building zensical site for version: ${docs_version}"
    rm -rf "$build_dir"
    uv run zensical build --clean
    mkdir -p "$(dirname "$build_dir")"
    mv build/docs "$build_dir"
}

copy_docs() {
    local build_dir=$1
    local output_dir=$2

    # Always clean out anything present so we don't orphan deleted pages
    rm -rf "$output_dir"
    mkdir -p "$output_dir"
    cp -r "$build_dir"/* "$output_dir/"
}

# Build "next" docs
if [ "${BRANCH_NAME}" = "${NEXT_BRANCH}" ]; then
    build_docs "next" "build/next"
    copy_docs "build/next" "docs-public/en/next"
fi

# Build "latest" docs
if [ "${BRANCH_NAME}" = "${LATEST_BRANCH}" ]; then
    build_docs "latest" "build/latest"
    copy_docs "build/latest" "docs-public/en/latest"
fi

# Build versioned docs for a valid tag
if [ -n "${TAG_NAME}" ] && [[ "$TAG_NAME" =~ ^v[0-9]+\.[0-9]+([\.a-z0-9]+)?$ ]]; then
    build_docs "$BRANCH_NAME" "build/${BRANCH_NAME}"
    copy_docs "build/${BRANCH_NAME}" "docs-public/en/${BRANCH_NAME}"

    if [ "${BRANCH_NAME}" = "${LATEST_BRANCH}" ]; then
        echo "Generating /page redirects"
        mkdir -p "docs-public/page/"
        DOCS_VERSION=$BRANCH_NAME uv run python scripts/generate_redirect_pages.py
    fi
fi

# Local build only
if [[ -z "${TAG_NAME}" ]] && [[ "${BRANCH_NAME}" != "${LATEST_BRANCH}" && "${BRANCH_NAME}" != "${NEXT_BRANCH}" ]]; then
    echo "Performing local build for branch: ${BRANCH_NAME}"
    build_docs "$BRANCH_NAME" "build/local"
    echo "Docs built to build/local/"
    echo "Preview with: uv run zensical serve"
fi
