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
FOCAL_HOME = Path.home() / ".focal"


def _migrate_legacy_config() -> None:
    """Move config.json / status_map.json from SCRIPT_DIR to FOCAL_HOME if needed."""
    FOCAL_HOME.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "status_map.json"):
        old = SCRIPT_DIR / name
        new = FOCAL_HOME / name
        if old.exists() and not new.exists():
            old.rename(new)
            import typer as _typer

            _typer.echo(f"Migrated {name} → {new}")


# ── focal board ───────────────────────────────────────────────────────────────


@board_app.command("sync")
def board_sync():
    """Sync personal board with all tracked origin project boards."""
    from focal import log, notify
    from focal.config import Config
    from focal.sync import Syncer, load_status_map

    _migrate_legacy_config()
    config_path = FOCAL_HOME / "config.json"
    if not config_path.exists():
        typer.echo(
            "ERROR: config.json not found. Run: python3 focal.py board setup", err=True
        )
        raise typer.Exit(1)

    cfg = Config.load(config_path)
    logger = log.setup(cfg.log_dir)
    status_map = load_status_map(FOCAL_HOME / "status_map.json")

    try:
        Syncer(cfg, status_map).run()
    except Exception as e:
        logger.error(str(e))
        if cfg.notifications:
            notify.notify("Focal sync failed", str(e))
        raise typer.Exit(1)


@board_app.command("setup")
def board_setup():
    """Interactive wizard — configure Focal for the first time."""
    from focal.wizard import run

    _migrate_legacy_config()
    run(FOCAL_HOME)


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
    console.print(f"  • {FOCAL_HOME / 'config.json'}")
    console.print(f"  • {FOCAL_HOME / 'status_map.json'}")
    console.print(f"  • {FOCAL_HOME / 'state.json'}")
    console.print(f"  • {FOCAL_HOME / 'logs'}/")
    console.print("  • ~/Library/LaunchAgents/com.*.focal.plist  (if installed)\n")

    if not yes and not Confirm.ask("Proceed?", default=False):
        raise typer.Exit(0)

    removed = []

    for path in (FOCAL_HOME / "config.json", FOCAL_HOME / "status_map.json"):
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

    from focal.config import Config
    from focal.pm.init_cmd import run

    _migrate_legacy_config()
    config: Config | None = None
    config_path = FOCAL_HOME / "config.json"
    if config_path.exists():
        config = Config.load(config_path)

    run(
        repo,
        repo_root.resolve(),
        config=config,
        config_path=config_path if config else None,
    )


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
    config_path = FOCAL_HOME / "config.json"
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
    config_path = FOCAL_HOME / "config.json"
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
    config_path = FOCAL_HOME / "config.json"
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
    config_path = FOCAL_HOME / "config.json"
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
    config_path = FOCAL_HOME / "config.json"
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
    config_path = FOCAL_HOME / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = _json.load(f)

    run(repo, repo_root.resolve(), config)


@cache_app.command("refresh-all")
def cache_refresh_all(
    force: bool = typer.Option(
        False, "--force", "-f", help="Ignore auto_cache_refresh flag and size limits."
    ),
):
    """Re-fetch state for all PM-managed repos registered in ~/.focal/config.json."""
    import json as _json

    from rich.console import Console

    from focal.config import Config
    from focal.pm import pm_state
    from focal.pm.sync_state_cmd import run

    _migrate_legacy_config()
    console = Console()
    config_path = FOCAL_HOME / "config.json"
    if not config_path.exists():
        typer.echo("ERROR: config.json not found. Run: focal board setup", err=True)
        raise typer.Exit(1)

    cfg = Config.load(config_path)

    if not force and not cfg.auto_cache_refresh:
        console.print(
            "[yellow]Auto cache refresh is disabled (auto_cache_refresh: false in config).[/yellow]\n"
            "Run manually with [bold]focal cache refresh-all --force[/bold] or "
            "set [bold]auto_cache_refresh: true[/bold] in ~/.focal/config.json to re-enable."
        )
        raise typer.Exit(0)

    if not cfg.pm_repos:
        console.print(
            "[yellow]No PM repos registered. Run [bold]focal pm init[/bold] for each repo first.[/yellow]"
        )
        raise typer.Exit(0)

    config_dict: dict = {}
    with open(config_path) as f:
        config_dict = _json.load(f)

    errors = 0
    skipped = 0
    for entry in cfg.pm_repos:
        repo = entry["repo"]
        repo_root = Path(entry["repo_root"])

        # Count tracked issues before fetching
        state = pm_state.load(repo_root)
        tracked = len(state["epics"]) + sum(
            len(e.get("stories", [])) for e in state["epics"]
        )
        if not force and tracked > cfg.max_tracked_issues:
            console.print(
                f"\n[yellow]⚠[/yellow]  Skipping [bold]{repo}[/bold] — "
                f"{tracked} tracked issues exceeds limit of {cfg.max_tracked_issues}.\n"
                f"   Run [bold]focal cache refresh {repo} --repo-root {repo_root}[/bold] manually, "
                f"or raise [bold]max_tracked_issues[/bold] in ~/.focal/config.json."
            )
            skipped += 1
            continue

        console.print(
            f"\n[bold cyan]Refreshing {repo}[/bold cyan] ({tracked} tracked issues)"
        )
        try:
            run(repo, repo_root, config_dict)
        except Exception as e:
            console.print(f"  [red]✖[/red] {e}")
            errors += 1

    if skipped:
        console.print(
            f"\n[yellow]{skipped} repo(s) skipped due to size limit.[/yellow]"
        )
    if errors:
        raise typer.Exit(1)


@cache_app.command("status")
def cache_status():
    """Show cache health: last sync time, tracked issue counts, and auto-refresh config."""
    from datetime import datetime, timezone

    from rich.console import Console
    from rich.table import Table

    from focal.config import Config
    from focal.pm import pm_state

    _migrate_legacy_config()
    console = Console()
    config_path = FOCAL_HOME / "config.json"
    if not config_path.exists():
        typer.echo("ERROR: config.json not found. Run: focal board setup", err=True)
        raise typer.Exit(1)

    cfg = Config.load(config_path)

    auto = (
        "[green]enabled[/green]"
        if cfg.auto_cache_refresh
        else "[yellow]disabled[/yellow]"
    )
    console.print(
        f"\n[bold]Focal cache status[/bold]  (auto-refresh: {auto}  |  limit: {cfg.max_tracked_issues} issues)\n"
    )

    if not cfg.pm_repos:
        console.print(
            "[dim]No PM repos registered. Run [bold]focal pm init[/bold] first.[/dim]"
        )
        raise typer.Exit(0)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Repo")
    table.add_column("Epics", justify="right")
    table.add_column("Stories", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Last synced")
    table.add_column("Status")

    now = datetime.now(timezone.utc)
    for entry in cfg.pm_repos:
        repo = entry["repo"]
        repo_root = Path(entry["repo_root"])
        state = pm_state.load(repo_root)

        epics = len(state["epics"])
        stories = sum(len(e.get("stories", [])) for e in state["epics"])
        total = epics + stories

        last_synced = state.get("last_synced")
        if last_synced:
            dt = datetime.fromisoformat(last_synced)
            age_h = (now - dt).total_seconds() / 3600
            synced_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            if age_h < 1:
                age_label = "[green]< 1h ago[/green]"
            elif age_h < 24:
                age_label = f"[green]{age_h:.0f}h ago[/green]"
            elif age_h < 72:
                age_label = f"[yellow]{age_h / 24:.0f}d ago[/yellow]"
            else:
                age_label = f"[red]{age_h / 24:.0f}d ago[/red]"
        else:
            synced_str = "never"
            age_label = "[red]never[/red]"

        if total > cfg.max_tracked_issues:
            size_status = f"[yellow]⚠ over limit ({total})[/yellow]"
        else:
            size_status = "[green]✔ ok[/green]"

        table.add_row(
            repo,
            str(epics),
            str(stories),
            str(total),
            f"{synced_str} ({age_label})",
            size_status,
        )

    console.print(table)
    console.print()

    if not cfg.auto_cache_refresh:
        console.print(
            "[dim]Auto-refresh is off. Run [bold]focal cache refresh-all --force[/bold] to refresh manually.[/dim]"
        )


if __name__ == "__main__":
    app()
