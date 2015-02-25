#!/bin/sh

VERSION=`python setup.py --version`

echo "Releasing v$VERSION..."

echo "build & commit the docs..."
python docs/build.py
git add docs/modules/*.md
git add docs/api/*.md
git commit -m "Documentation update for v$VERSION"
git push

echo "git..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags

echo "pypi..."
python setup.py sdist upload

echo "Done!"
