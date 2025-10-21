#!/usr/bin/env bash

set -euo pipefail

echo "Execute ruff format..."
uv run ruff format

echo "Execute ruff check..."
uv run ruff check

echo "Execute mypy..."
uv run mypy

echo "Linting complete!"
