#!/usr/bin/env bash
source "$(dirname "$0")/common.bash"    # setup $uvrun, etc.

echo "Execute local end to end tests..."
$uvrun pytest -m end_to_end_local

echo "Execute SSH end to end tests..."
$uvrun pytest -m end_to_end_ssh

echo "Execute Docker end to end tests..."
$uvrun pytest -m end_to_end_docker

echo "Tests complete!"
