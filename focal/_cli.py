"""Entry point for the installed `focal` command.

`focal.py` at the repo root cannot be imported as a module named `focal`
(it would shadow the `focal/` package). This shim imports it by file path
so the package entry point `focal._cli:app` works after `pip install`.
"""

import importlib.util
from pathlib import Path


def _load_focal_py():
    root = Path(__file__).parent.parent / "focal.py"
    spec = importlib.util.spec_from_file_location("_focal_main", root)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _load_focal_py()
app = _mod.app


def main():
    app()


if __name__ == "__main__":
    main()
