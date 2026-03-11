#!/usr/bin/env bash

set -euo pipefail

echo "Execute ruff format..."
uv run ruff format
