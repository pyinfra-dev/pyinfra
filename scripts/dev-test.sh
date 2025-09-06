#!/usr/bin/env bash

set -euo pipefail

echo "Execute pytest..."
uv run pytest $@

echo "Tests complete!"
