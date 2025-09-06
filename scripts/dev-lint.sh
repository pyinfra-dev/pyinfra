#!/usr/bin/env bash

set -euo pipefail

echo "Execute black..."
uv run black ./

echo "Execute flake8..."
uv run flake8

echo "Execute mypy..."
uv run mypy

echo "Linting complete!"
