#!/bin/sh

VERSION=`python setup.py --version`

echo "# Releasing pyinfra v$VERSION..."

echo "# Build the docs..."
python scripts/build_docs.py

echo "# Commit & push the docs..."
git add docs/
git add README.md
git commit -m "Documentation update for v$VERSION"
git push

echo "# Git tag & push..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags

echo "# Upload to pypi..."
python setup.py sdist upload

echo "# All done!"
