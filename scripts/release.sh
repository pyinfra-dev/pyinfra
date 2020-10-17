#!/bin/sh

set -e

VERSION=`python setup.py --version`
MAJOR_BRANCH="`python setup.py --version | cut -d'.' -f1`.x"

echo "# Releasing pyinfra v${VERSION} (branch ${MAJOR_BRANCH})"

echo "# Running tests..."
pytest

echo "# Git tag & push..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags

echo "Git update major branch..."
git checkout $MAJOR_BRANCH
git merge master
git push
git checkout master

echo "# Upload to pypi..."
# Clear build & dist
rm -rf build/* dist/*
# Build source and wheel packages
python setup.py sdist bdist_wheel
# Upload w/Twine
twine upload dist/*

echo "# All done!"
