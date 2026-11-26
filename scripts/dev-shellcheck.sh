#!/usr/bin/env bash

set -euo pipefail

if ! command -v shellcheck >/dev/null 2>&1; then
    echo "shellcheck is not installed, see docs/contributing.md for instructions." >&2
    exit 1
fi

git grep -l '^#\( *shellcheck \|!\(/bin/\|/usr/bin/env \)\(sh\|bash\|dash\|ksh\)\)' -- ':!*.py' \
    | xargs shellcheck
