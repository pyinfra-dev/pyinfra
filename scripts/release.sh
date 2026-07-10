#!/usr/bin/env bash
source "$(dirname "$0")/common.bash"    # setup $uvrun, etc.

VERSION=$($uvrun python scripts/generate_next_version.py)
MAJOR_BRANCH="$($uvrun python scripts/generate_next_version.py | cut -d'.' -f1).x"

echo "# Releasing pyinfra v${VERSION} (branch ${MAJOR_BRANCH})"

echo "# Running tests..."
$uvrun pytest

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
$uvrun python scripts/make_github_release.py

echo "# All done!"
