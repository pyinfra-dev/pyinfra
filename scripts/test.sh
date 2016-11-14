#!/bin/sh

TEST=$1

echo "### pyinfra Tests"

# Remove any cached coverage data
rm -f .coverage


if [ ! -f tests/test_${TEST}.py ]; then
    echo "--> Testing everything..."
    nosetests --with-coverage --cover-package pyinfra $@
else
    echo "--> Testing ${TEST}..."
    ARGS="${@:2}"
    nosetests tests.test_${TEST} --with-coverage --cover-package pyinfra.${TEST} $ARGS
fi
