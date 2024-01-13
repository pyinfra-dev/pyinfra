#!/bin/sh

set -eu

# This file is intentionally excluded in mypy config for normal runs so the un-stubbed operation.py
# can be type-checked against the rest of the codebase.
mypy pyinfra/api/operation.pyi

# The flow checks ensure the operation stub above is working as expected, when passing a direct
# file into mypy it seems to (usefully) ignore the exclude config, so we can confirm valid/invalid
# operation calls.

for file in $(ls tests/typing/valid); do
    mypy tests/typing/valid/$file || (echo "FAIL VALID $file" && exit 1)
    echo "OK VALID $file"
done

for file in $(ls tests/typing/invalid); do
    mypy tests/typing/invalid/$file && (echo "FAIL INVALID $file" && exit 1)
    echo "OK INVALID $file"
done
