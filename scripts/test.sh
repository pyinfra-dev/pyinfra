#!/bin/sh

TEST=$1

echo "### pyinfra Tests"

# Remove any cached coverage data
rm -f .coverage

if [ -z $TEST ]; then
    echo "--> Testing everything..."
    nosetests --with-coverage --cover-package pyinfra.api,pyinfra.modules,pyinfra.facts
else
    if [ ! -f tests/test_${TEST}.py ]; then
        echo "--> Missing test file tests/test_${TEST}!"
        exit 1
    fi

    echo "--> Testing ${TEST}..."
    nosetests tests.test_${TEST} --with-coverage --cover-package pyinfra.${TEST}
fi
