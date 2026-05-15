#!/usr/bin/env python3
"""Focal CLI — bidirectional GitHub Projects sync + project management."""

from pathlib import Path

import typer

app = typer.Typer(
    name="focal",
    help="Focal — sync your personal GitHub Projects board and manage project delivery.",
    no_args_is_help=True,
)

# focal board — personal board sync commands
board_app = typer.Typer(help="Personal board sync commands.")
app.add_typer(board_app, name="board")

# focal pm — project management commands
pm_app = typer.Typer(help="Project management commands (epics, stories, planning).")
app.add_typer(pm_app, name="pm")

# focal cache — local state cache management
cache_app = typer.Typer(help="Manage the local state cache (docs/focal/.cache/).")
app.add_typer(cache_app, name="cache")

SCRIPT_DIR = Path(__file__).parent


# ── focal board ───────────────────────────────────────────────────────────────


@board_app.command("sync")
def board_sync():
    """Sync personal board with all tracked origin project boards."""
    from focal import log
    from focal.config import Config
    from focal.sync import Syncer, load_status_map

    config_path = SCRIPT_DIR / "config.json"
    if not config_path.exists():
        typer.echo(
            "ERROR: config.json not found. Run: python3 focal.py board setup", err=True
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


@board_app.command("setup")
def board_setup():
    """Interactive wizard — configure Focal for the first time."""
    from focal.wizard import run

    run(SCRIPT_DIR)


# ── focal reset ───────────────────────────────────────────────────────────────


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
):
    """Remove all Focal config, state, logs, and the launchd scheduler."""
    import shutil
    import subprocess

    from rich.console import Console
    from rich.prompt import Confirm

    console = Console()
    console.print("\n[bold red]  ⚠  Focal Reset[/bold red]\n")
    console.print("This will remove:")
    console.print(f"  • {SCRIPT_DIR / 'config.json'}")
    console.print(f"  • {SCRIPT_DIR / 'status_map.json'}")
    console.print("  • ~/.focal/state.json")
    console.print("  • ~/.focal/logs/")
    console.print("  • ~/Library/LaunchAgents/com.*.focal.plist  (if installed)\n")

    if not yes and not Confirm.ask("Proceed?", default=False):
        raise typer.Exit(0)

    removed = []

    for path in (SCRIPT_DIR / "config.json", SCRIPT_DIR / "status_map.json"):
        if path.exists():
            path.unlink()
            removed.append(str(path))

    focal_dir = Path.home() / ".focal"
    if focal_dir.exists():
        shutil.rmtree(focal_dir)
        removed.append(str(focal_dir))

    launch_agents = Path.home() / "Library" / "LaunchAgents"
    for plist in launch_agents.glob("*.focal.plist"):
        label = plist.stem
        subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
        plist.unlink()
        removed.append(str(plist))
        console.print(f"  [green]✔[/green] Unloaded launchd job: {label}")

    if removed:
        for r in removed:
            console.print(f"  [green]✔[/green] Removed: {r}")
        console.print("\n[bold green]Reset complete.[/bold green]")
        console.print("Run [bold]python3 focal.py board setup[/bold] to start fresh.")
    else:
        console.print("[dim]Nothing to remove — Focal was not configured.[/dim]")


# ── focal pm ──────────────────────────────────────────────────────────────────


@pm_app.command("init")
def pm_init(
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


@pm_app.command("epic-create")
def pm_epic_create(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."), "--repo-root", help="Local path to the repo root"
    ),
    title: str = typer.Option(None, "--title", help="Epic title (skips prompt)"),
    description: str = typer.Option(
        None, "--description", help="One-line description (skips prompt)"
    ),
    sp: int = typer.Option(None, "--sp", help="Story point estimate (skips prompt)"),
):
    """Create a GitHub epic and update docs/focal/epics.md."""
    import json as _json

    from focal.pm.epic_cmd import run

    config: dict = {}
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    run(repo, repo_root.resolve(), config, title=title, description=description, sp=sp)


@pm_app.command("story-create")
def pm_story_create(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."), "--repo-root", help="Local path to the repo root"
    ),
    epic_id: str = typer.Option(
        None, "--epic", help="Epic ID to attach to, e.g. E1 (skips prompt)"
    ),
    title: str = typer.Option(None, "--title", help="Story title (skips prompt)"),
    description: str = typer.Option(
        None, "--description", help="One-line description (skips prompt)"
    ),
    sp: int = typer.Option(None, "--sp", help="Story point estimate (skips prompt)"),
):
    """Create a story linked to an epic and update docs/focal/epics.md."""
    import json as _json

    from focal.pm.story_cmd import run

    config: dict = {}
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    run(
        repo,
        repo_root.resolve(),
        config,
        epic_id=epic_id,
        title=title,
        description=description,
        sp=sp,
    )


@pm_app.command("plan")
def pm_plan(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."), "--repo-root", help="Local path to the repo root"
    ),
    refresh: bool = typer.Option(
        False, "--refresh", help="Re-fetch state from GitHub before planning"
    ),
    weeks: int = typer.Option(
        None, "--weeks", help="Iteration length in weeks (skips prompt)"
    ),
    start_date: str = typer.Option(
        None, "--start", help="Start date YYYY-MM-DD (skips prompt)"
    ),
    team: str = typer.Option(
        None,
        "--team",
        help="Team capacity as 'handle:sp,handle:sp', e.g. 'alice:8,bob:6' (skips prompt)",
    ),
    pto: list[str] = typer.Option(
        None,
        "--pto",
        help="PTO entry as 'handle:YYYY-MM-DD:YYYY-MM-DD' (repeatable, skips prompt)",
    ),
    goals: str = typer.Option(
        None,
        "--goals",
        help="Iteration goals as 'I1:goal text,I2:goal text' (skips prompt)",
    ),
):
    """Generate or update docs/focal/iteration-planning.md."""
    import json as _json

    from focal.pm.plan_cmd import run

    config: dict = {}
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    # Parse goals string into dict
    goals_dict: dict | None = None
    if goals:
        goals_dict = {}
        for part in goals.split(","):
            if ":" in part:
                label, goal_text = part.split(":", 1)
                goals_dict[label.strip()] = goal_text.strip()

    run(
        repo,
        repo_root.resolve(),
        config,
        refresh=refresh,
        weeks=weeks,
        start_date=start_date,
        team=team,
        pto=pto or None,
        goals=goals_dict,
    )


@pm_app.command("retro")
def pm_retro(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."), "--repo-root", help="Local path to the repo root"
    ),
    refresh: bool = typer.Option(
        False, "--refresh", help="Re-fetch state from GitHub before logging retro"
    ),
    iteration: str = typer.Option(
        None, "--iteration", help="Iteration label, e.g. I1 (skips prompt)"
    ),
    goal_met: bool = typer.Option(
        None,
        "--goal-met/--no-goal-met",
        help="Whether the iteration goal was met (skips prompt)",
    ),
    went_well: list[str] = typer.Option(
        None, "--went-well", help="What went well (repeatable, skips prompt)"
    ),
    to_improve: list[str] = typer.Option(
        None, "--to-improve", help="What to improve (repeatable, skips prompt)"
    ),
    action: list[str] = typer.Option(
        None,
        "--action",
        help="Action item as 'handle:description:YYYY-MM-DD' (repeatable, skips prompt)",
    ),
    notes: str = typer.Option(None, "--notes", help="Free-form notes (skips prompt)"),
):
    """Log a completed iteration and update docs/focal/retro-log.md."""
    import json as _json

    from focal.pm.retro_cmd import run

    config: dict = {}
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    # Parse action items
    action_items: list[dict] | None = None
    if action:
        action_items = []
        for a in action:
            parts = a.split(":", 2)
            handle = parts[0].lstrip("@") if len(parts) > 0 else ""
            description = parts[1] if len(parts) > 1 else ""
            due = parts[2] if len(parts) > 2 else ""
            action_items.append({"handle": handle, "action": description, "due": due})

    run(
        repo,
        repo_root.resolve(),
        config,
        refresh=refresh,
        iteration_label=iteration,
        goal_met=goal_met,
        went_well=went_well or None,
        to_improve=to_improve or None,
        action_items=action_items,
        notes=notes,
    )


@pm_app.command("status")
def pm_status(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root (default: current directory)",
    ),
    refresh: bool = typer.Option(
        False, "--refresh", help="Re-fetch state from GitHub before displaying status."
    ),
):
    """Print a live terminal summary of the current iteration progress."""
    import json as _json

    from focal.pm.status_cmd import run

    config: dict = {}
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    run(repo, repo_root.resolve(), config, refresh=refresh)


# ── focal cache ───────────────────────────────────────────────────────────────


@cache_app.command("refresh")
def cache_refresh(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root (default: current directory)",
    ),
):
    """Re-fetch all epic/story state from GitHub and update docs/focal/.cache/."""
    import json as _json

    from focal.pm.sync_state_cmd import run

    config: dict = {}
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    run(repo, repo_root.resolve(), config)


@pm_app.command("plan")
def pm_plan(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root (default: current directory)",
    ),
    refresh: bool = typer.Option(
        False, "--refresh", help="Re-fetch state from GitHub before planning."
    ),
):
    """Generate or update docs/focal/iteration-planning.md."""
    import json as _json

    from focal.pm.plan_cmd import run

    config: dict = {}
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    run(repo, repo_root.resolve(), config, refresh=refresh)


# ── focal cache ───────────────────────────────────────────────────────────────


@cache_app.command("refresh")
def cache_refresh(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root (default: current directory)",
    ),
):
    """Re-fetch all epic/story state from GitHub and update docs/focal/.cache/."""
    import json as _json

    from focal.pm.sync_state_cmd import run

    config: dict = {}
    config_path = SCRIPT_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    run(repo, repo_root.resolve(), config)


if __name__ == "__main__":
    app()
