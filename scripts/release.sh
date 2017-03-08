#!/bin/sh

set -e

VERSION=`python setup.py --version`

echo "# Releasing pyinfra v$VERSION..."

echo "# Checking pandoc installed..."
pandoc --help >/dev/null 2>&1 || (echo "pandoc is not installed!" && exit 1)
python -c 'import pypandoc' >/dev/null 2>&1 || (echo "pypandoc is not installed!" && exit 1)

echo "# Running tests..."
nosetests -s

echo "# Build the docs..."
scripts/build_docs.sh

echo "# Commit & push the docs..."
git add docs/
git commit -m "Documentation update for v$VERSION." || echo "No docs updated!"
git push

echo "# Git tag & push..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags

echo "# Upload to pypi..."
# Clear build & dist
rm -rf build/* dist/*
# Build source and wheel packages
python setup.py sdist bdist_wheel
# Upload w/Twine
twine upload dist/*

echo "# All done!"
