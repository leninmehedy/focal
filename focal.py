#!/usr/bin/env python3
"""Focal CLI — bidirectional GitHub Projects sync."""

from pathlib import Path

import typer

app = typer.Typer(
    name="focal",
    help="Focal — sync your personal GitHub Projects board with origin repo boards.",
    no_args_is_help=True,
)

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


if __name__ == "__main__":
    app()
