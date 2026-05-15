#!/usr/bin/env python3
"""Focal CLI — bidirectional GitHub Projects sync + project management."""

from pathlib import Path

import typer

app = typer.Typer(
    name="focal",
    help="Focal — sync your personal GitHub Projects board and manage project delivery.",
    no_args_is_help=True,
)

# Sub-app for project management commands
pm_app = typer.Typer(help="Project management commands (epics, stories, planning).")
app.add_typer(pm_app, name="pm")

SCRIPT_DIR = Path(__file__).parent


@app.command()
def sync():
    """Sync personal board with all tracked origin project boards."""
    from focal import log
    from focal.config import Config
    from focal.sync import Syncer, load_status_map

    config_path = SCRIPT_DIR / "config.json"
    if not config_path.exists():
        typer.echo(
            "ERROR: config.json not found. Run: python3 focal.py setup", err=True
        )
        raise typer.Exit(1)

    cfg = Config.load(config_path)
    logger = log.setup(cfg.log_dir)
    status_map = load_status_map(SCRIPT_DIR / "status_map.json")

    try:
        Syncer(cfg, status_map).run()
    except Exception as e:
        logger.error(str(e))
        raise typer.Exit(1)


@app.command()
def setup():
    """Interactive wizard — configure Focal for the first time."""
    from focal.wizard import run

    run(SCRIPT_DIR)


@app.command()
def init(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root (default: current directory)",
    ),
):
    """Bootstrap a repo with Focal project management structure."""
    from focal.pm.init_cmd import run

    run(repo, repo_root.resolve())


if __name__ == "__main__":
    app()
