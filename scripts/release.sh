#!/usr/bin/env bash

set -euo pipefail

VERSION=$(uv run python scripts/generate_next_version.py)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
MAJOR_BRANCH="$(echo "${VERSION}" | cut -d'.' -f1).x"
MINOR_BRANCH="$(echo "${VERSION}" | cut -d'.' -f1-2).x"

if [ "${BRANCH}" != "${MAJOR_BRANCH}" ] && [ "${BRANCH}" != "${MINOR_BRANCH}" ]; then
    echo "Refusing to release v${VERSION} from ${BRANCH} (expected ${MAJOR_BRANCH} or ${MINOR_BRANCH})"
    exit 1
fi

echo "# Releasing pyinfra v${VERSION} (branch ${BRANCH})"

echo "# Running tests..."
uv run pytest

echo "# Git tag & push..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --atomic origin "${BRANCH}" "v$VERSION"

echo "Clear existing build/dist..."
rm -rf build/* dist/*
echo "Build source and wheel packages..."
uv build
echo "Publishing to PyPI..."
uv publish

echo "Making GitHub release..."
uv run python scripts/make_github_release.py

echo "# All done!"
