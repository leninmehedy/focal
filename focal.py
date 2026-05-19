#!/usr/bin/env python3
"""Thin wrapper so `python3 focal.py <cmd>` still works from the repo root.

The real CLI implementation lives in focal/_cli.py, which is the installed
entry point when the package is installed via pip/pipx.
"""

from focal._cli import main

if __name__ == "__main__":
    main()
