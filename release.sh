#!/bin/sh

VERSION=`python setup.py --version`

echo "Releasing v$VERSION..."

echo "build & commit the docs..."
python docs/buil.py
git add docs/modules/*.md
git commit -m 'Documentation update'
git push

echo "git..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags

echo "pypi..."
python setup.py sdist upload

echo "Done!"
