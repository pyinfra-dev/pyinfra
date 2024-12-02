#!/usr/bin/env bash

set -euo pipefail

echo "Execute pytest..."
pytest $@

echo "Tests complete!"
