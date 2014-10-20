#!/bin/sh

VERSION=`python setup.py --version`

echo "Releasing v$VERSION..."

echo "git..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags

echo "pypi..."
python setup.py sdist upload

echo "Done!"
