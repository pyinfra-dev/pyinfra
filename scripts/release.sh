#!/bin/sh

set -euo pipefail

VERSION=`uv run python scripts/generate_next_version.py`
MAJOR_BRANCH="`uv run python scripts/generate_next_version.py | cut -d'.' -f1`.x"

echo "# Releasing pyinfra v${VERSION} (branch ${MAJOR_BRANCH})"

echo "# Running tests..."
uv run pytest

echo "# Git tag & push..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --atomic origin "${MAJOR_BRANCH}" "v$VERSION"

echo "Clear existing build/dist..."
rm -rf build/* dist/*
echo "Build source and wheel packages..."
uv build
echo "Publishing to PyPI..."
uv publish

echo "Making GitHub release..."
uv run python scripts/make_github_release.py

echo "# All done!"
