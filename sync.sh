#!/usr/bin/env bash
# Thin wrapper — delegates to the Python CLI.
exec python3 "$(dirname "$0")/focal.py" sync "$@"
