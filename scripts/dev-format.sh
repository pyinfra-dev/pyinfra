#!/usr/bin/env bash
source "$(dirname "$0")/common.bash"    # setup $uvrun, etc.

echo "Execute ruff format..."
$uvrun ruff format
