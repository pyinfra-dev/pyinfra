#!/bin/sh

BRANCH_NAME=`git rev-parse --abbrev-ref HEAD`

case "${BRANCH_NAME}" in
    "2.x")
        DOCS_VERSION="2.x"
        IS_LATEST="true"
        ;;
    "1.x")
        DOCS_VERSION="1.x"
        ;;
    "0.x")
        DOCS_VERSION="0.x"
        ;;
esac

if [ -z "${DOCS_VERSION}" ]; then
    echo "No docs version for this branch, noop!"
    exit 0
fi

echo "Building docs branch=${BRANCH_NAME}, version=${DOCS_VERSION}"
env DOCS_VERSION=$DOCS_VERSION sphinx-build -a docs/ docs/public/en/$DOCS_VERSION/

if [ -n "${IS_LATEST}" ]; then
    echo "Building docs branch=${BRANCH_NAME}, version=latest"
    env DOCS_VERSION=latest sphinx-build -a docs/ docs/public/en/latest/
fi
