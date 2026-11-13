#!/usr/bin/env bash

set -euo pipefail

echo "Execute ruff check..."
uv run ruff check --diff --unsafe-fixes
uv run ruff format --diff

echo "Execute mypy..."
uv run mypy

echo "Execute arguments type check..."
uv run python scripts/lint_arguments_sync.py

echo "Execute operation argument check..."
uv run python scripts/lint_operation_arguments.py

echo "Execute shellcheck..."
scripts/dev-shellcheck.sh

echo "Linting complete!"
