#!/bin/sh

TEST=$1

echo "### pyinfra Tests"

# Remove any cached coverage data
rm -f .coverage

if [ ! -f tests/test_${TEST}.py ]; then
    echo "--> Testing everything:"
    ARGS="--cover-package pyinfra --cover-package pyinfra_cli $@"
else
    echo "--> Testing ${TEST}..."
    ARGS="${@:2}"

    if [ "${TEST}" = "cli" ]; then
        ARGS="tests.test_${TEST} --cover-package pyinfra_${TEST} ${ARGS}"
    else
        ARGS="tests.test_${TEST} --cover-package pyinfra.${TEST} ${ARGS}"
    fi
fi

COMMAND="nosetests --with-coverage ${ARGS}"
echo "--> ${COMMAND}"
$COMMAND
