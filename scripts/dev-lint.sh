#!/usr/bin/env bash
source "$(dirname "$0")/common.bash"    # setup $uvrun, etc.

echo "Execute ruff check..."
$uvrun ruff check --diff --unsafe-fixes
$uvrun ruff format --diff

echo "Execute mypy..."
$uvrun mypy

echo "Execute arguments type check..."
$uvrun python scripts/lint_arguments_sync.py

echo "Execute shellcheck..."
if ! command -v shellcheck >/dev/null 2>&1; then
    echo "shellcheck is not installed, see docs/contributing.md for instructions." >&2
    exit 1
fi

git grep -l '^#\( *shellcheck \|!\(/bin/\|/usr/bin/env \)\(sh\|bash\|dash\|ksh\)\)' -- ':!*.py' \
    | xargs shellcheck -x -P scripts/

echo "Linting complete!"
