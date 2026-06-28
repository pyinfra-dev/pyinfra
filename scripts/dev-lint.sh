#!/usr/bin/env bash

set -euo pipefail

echo "Execute ruff check..."
uv run ruff check --diff --unsafe-fixes
uv run ruff format --diff

echo "Execute mypy..."
uv run mypy

echo "Execute arguments type check..."
uv run python scripts/lint_arguments_sync.py

echo "Execute shellcheck..."
if ! command -v shellcheck >/dev/null 2>&1; then
    echo "shellcheck is not installed, see docs/contributing.md for instructions." >&2
    exit 1
fi
git grep -l '^#\( *shellcheck \|!\(/bin/\|/usr/bin/env \)\(sh\|bash\|dash\|ksh\)\)' -- ':!*.py' \
    | xargs shellcheck

echo "Linting complete!"
