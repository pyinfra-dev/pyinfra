#!/usr/bin/env bash

set -euo pipefail

echo "Execute local end to end tests..."
uv run pytest -m end_to_end_local

echo "Execute SSH end to end tests..."
uv run pytest -m end_to_end_ssh

echo "Execute Docker end to end tests..."
uv run pytest -m end_to_end_docker

echo "Tests complete!"
