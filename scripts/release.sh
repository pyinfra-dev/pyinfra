#!/bin/sh

set -euo pipefail

VERSION=`python setup.py --version`
MAJOR_BRANCH="`python setup.py --version | cut -d'.' -f1`.x"

IS_DEV=false
if [[ `python setup.py --version` =~ "dev" ]]; then
    IS_DEV=true
fi

echo "# Releasing pyinfra v${VERSION} (branch ${MAJOR_BRANCH}, dev=${IS_DEV})"

echo "# Running tests..."
pytest

echo "# Git tag & push..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags

if [[ "${IS_DEV}" == "false" ]]; then
    echo "Git update major branch..."
    git checkout $MAJOR_BRANCH
    git merge master
    git push
    git checkout master
else
    echo "Skipping major branch due to dev release"
fi

echo "Clear existing build/dist..."
rm -rf build/* dist/*
echo "Build source and wheel packages..."
python setup.py sdist bdist_wheel
echo "Upload w/Twine..."
twine upload dist/*

echo "# All done!"
