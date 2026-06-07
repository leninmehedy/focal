"""Focal CLI — bidirectional GitHub Projects sync + project management."""

from pathlib import Path
from typing import Optional

import typer

try:
    from importlib.metadata import version as _pkg_version

    VERSION = _pkg_version("focal-cli")
except Exception:
    VERSION = "dev"

app = typer.Typer(
    name="focal",
    help="Focal — sync your personal GitHub Projects board and manage project delivery.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"focal {VERSION}")
        raise typer.Exit()


@app.callback()
def _callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


# focal board — personal board sync commands
board_app = typer.Typer(help="Personal board sync commands.")
app.add_typer(board_app, name="board")

# focal pm — project management commands
pm_app = typer.Typer(help="Project management commands (epics, stories, planning).")
app.add_typer(pm_app, name="pm")

# focal cache — local state cache management
cache_app = typer.Typer(help="Manage the local state cache (docs/focal/.cache/).")
app.add_typer(cache_app, name="cache")

SCRIPT_DIR = Path(
    __file__
).parent.parent  # repo root (focal/_cli.py → focal/ → repo root)
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


def _load_config(require: bool = True) -> "tuple[dict, Path]":
    """Load ~/.focal/config.json and return (config_dict, config_path).

    If require=True and the file is missing, print a clear actionable error and exit.
    If require=False and the file is missing, return ({}, path) so callers can warn
    and proceed with degraded functionality (no board integration).
    """
    import json as _json

    _migrate_legacy_config()
    config_path = FOCAL_HOME / "config.json"
    if not config_path.exists():
        if require:
            from rich.console import Console

            Console().print(
                "\n[bold red]Focal is not configured.[/bold red]\n\n"
                "Run [bold]focal board setup[/bold] to set up your personal board and config.\n"
                "This is required before using PM commands so Focal knows which board\n"
                "to add epics and stories to, and which GitHub account to use.\n"
            )
            raise typer.Exit(1)
        return {}, config_path
    with open(config_path) as f:
        return _json.load(f), config_path


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
        typer.echo("ERROR: config.json not found. Run: focal board setup", err=True)
        raise typer.Exit(1)

    cfg = Config.load(config_path)
    logger = log.setup(cfg.log_dir)
    status_map = load_status_map(FOCAL_HOME / "status_map.json")

    try:
        Syncer(cfg, status_map, config_path=config_path).run()
    except Exception as e:
        logger.error(str(e))
        if cfg.notifications:
            notify.notify("Focal sync failed", str(e))
        raise typer.Exit(1)


@board_app.command("status")
def board_status():
    """Show a live summary of the personal board — counts per column, by repo, blocked and recent items."""
    from datetime import datetime, timedelta, timezone

    from rich.console import Console
    from rich.table import Table

    from focal import gh

    config, _ = _load_config(require=True)
    board_number = int(config["board_number"])
    owner = config["board_owner"]

    console = Console()
    console.print(
        f"\nPersonal board — [bold]{owner}[/bold] (project #{board_number})\n"
    )

    items = gh.project_items(board_number, owner)

    def _parse_url(url: str) -> tuple[str, str]:
        """Return (repo, ref) from a GitHub issue URL."""
        parts = url.rstrip("/").split("/") if url else []
        if len(parts) >= 7:
            repo = f"{parts[3]}/{parts[4]}"
            ref = f"{repo}#{parts[6]}"
            return repo, ref
        return "", f"#{parts[-1]}" if parts else "#?"

    def _status_name(item: dict) -> str:
        s = item.get("status")
        if isinstance(s, dict):
            return s.get("name") or "(no status)"
        return str(s) if s else "(no status)"

    # ── Status counts table ───────────────────────────────────────────────────
    status_counts: dict[str, int] = {}
    for item in items:
        name = _status_name(item)
        status_counts[name] = status_counts.get(name, 0) + 1

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Status")
    table.add_column("Count", justify="right")
    for name, count in status_counts.items():
        table.add_row(name, str(count))
    table.add_section()
    table.add_row("[bold]Total[/bold]", f"[bold]{len(items)}[/bold]")
    console.print(table)

    # ── By-repo breakdown ─────────────────────────────────────────────────────
    # repo → {status_name: count}
    repo_breakdown: dict[str, dict[str, int]] = {}
    for item in items:
        content = item.get("content") or {}
        repo, _ = _parse_url(content.get("url", ""))
        if not repo:
            repo = "(unknown)"
        sname = _status_name(item)
        repo_breakdown.setdefault(repo, {})
        repo_breakdown[repo][sname] = repo_breakdown[repo].get(sname, 0) + 1

    if repo_breakdown:
        console.print("\n[bold]By repo[/bold]")
        repo_table = Table(show_header=False, box=None, padding=(0, 1))
        repo_table.add_column("Repo", style="cyan")
        repo_table.add_column("Total", justify="right")
        repo_table.add_column("Breakdown", style="dim")
        for repo, counts in sorted(repo_breakdown.items()):
            total = sum(counts.values())
            breakdown = "  ".join(f"{s}: {n}" for s, n in sorted(counts.items()))
            repo_table.add_row(repo, str(total), breakdown)
        console.print(repo_table)

    # ── Blocked items ─────────────────────────────────────────────────────────
    blocked = [item for item in items if "blocked" in _status_name(item).lower()]
    if blocked:
        console.print(f"\n[bold red]Blocked ({len(blocked)})[/bold red]")
        for item in blocked:
            content = item.get("content") or {}
            _, ref = _parse_url(content.get("url", ""))
            title = content.get("title", "(no title)")
            url = content.get("url", "")
            console.print(f"  • [red]{ref}[/red] — {title}")
            if url:
                console.print(f"    [dim]{url}[/dim]")

    # ── Recently added (last 7 days) ──────────────────────────────────────────
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = []
    for item in items:
        created_at = item.get("createdAt", "")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if dt >= cutoff:
                    recent.append((dt, item))
            except ValueError:
                pass
    recent.sort(key=lambda x: x[0], reverse=True)

    if recent:
        console.print(f"\n[bold]Recently added (last 7 days, {len(recent)})[/bold]")
        for _, item in recent:
            content = item.get("content") or {}
            _, ref = _parse_url(content.get("url", ""))
            title = content.get("title", "(no title)")
            sname = _status_name(item)
            console.print(f"  • {ref} — {title} [dim]({sname})[/dim]")

    console.print()


@board_app.command("setup")
def board_setup(
    owner: Optional[str] = typer.Option(
        None, "--owner", help="GitHub username or org (skips prompt)."
    ),
    board_title: str = typer.Option(
        "My Board", "--board-title", help="Title for a newly-created board."
    ),
    create_board: Optional[bool] = typer.Option(
        None,
        "--create-board/--use-board",
        help="Create a new board (default) or attach to an existing one.",
    ),
    board_number: Optional[int] = typer.Option(
        None,
        "--use-board-number",
        help="Existing board number to attach to (requires --use-board).",
    ),
    repos: Optional[str] = typer.Option(
        None,
        "--repos",
        help="Comma-separated repos to watch, e.g. owner/repo1,owner/repo2 (skips prompt).",
    ),
    assignee: Optional[str] = typer.Option(
        None,
        "--assignee",
        help="GitHub username for issue assignment filter (defaults to --owner).",
    ),
    done_status: str = typer.Option(
        "✅ Done",
        "--done-status",
        help="Exact name of the Done status column on your board.",
    ),
):
    """Interactive wizard — configure Focal for the first time.

    When --owner, --repos, and either --create-board or --use-board-number are
    supplied, runs non-interactively (no prompts).
    """
    from focal.wizard import run

    _migrate_legacy_config()

    repos_list: list[str] | None = (
        [r.strip() for r in repos.split(",") if r.strip()] if repos else None
    )
    effective_assignee = assignee or owner
    effective_create = True if create_board is None else create_board

    run(
        FOCAL_HOME,
        owner=owner,
        assignee=effective_assignee,
        repos=repos_list,
        create_board=effective_create,
        board_number=board_number,
        board_title=board_title,
        done_status=done_status,
    )


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

    import platform

    # Delete individual state files
    for path in (
        FOCAL_HOME / "config.json",
        FOCAL_HOME / "status_map.json",
        FOCAL_HOME / "state.json",
    ):
        if path.exists():
            path.unlink()

    # Delete logs directory
    logs_dir = FOCAL_HOME / "logs"
    if logs_dir.exists():
        shutil.rmtree(logs_dir)

    # Delete launchd plists on macOS
    if platform.system() == "Darwin":
        launch_agents = Path.home() / "Library" / "LaunchAgents"
        for plist in launch_agents.glob("com.*.focal*.plist"):
            subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
            plist.unlink()

    console.print(
        "\n[bold green]✔ Reset complete. Run 'focal board setup' to reconfigure.[/bold green]"
    )


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


@pm_app.command("remove-repo")
def pm_remove_repo(
    repo: str = typer.Argument(..., help="Repo to unregister, in owner/repo format"),
):
    """Remove a repo from the PM cache registry (~/.focal/config.json pm_repos)."""
    from rich.console import Console

    from focal.config import Config

    _migrate_legacy_config()
    console = Console()
    config_path = FOCAL_HOME / "config.json"
    if not config_path.exists():
        typer.echo("ERROR: config.json not found. Run: focal board setup", err=True)
        raise typer.Exit(1)

    cfg = Config.load(config_path)
    before = len(cfg.pm_repos)
    cfg.pm_repos = [e for e in cfg.pm_repos if e.get("repo") != repo]

    if len(cfg.pm_repos) == before:
        console.print(
            f"[yellow]{repo} is not in the PM registry — nothing to remove.[/yellow]"
        )
        raise typer.Exit(0)

    cfg.save(config_path)
    console.print(f"[green]✔[/green] Removed [bold]{repo}[/bold] from pm_repos.")
    console.print(
        "[dim]Local repo files are unchanged. Only the registry entry was removed.[/dim]"
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
    from_design: Optional[Path] = typer.Option(
        None,
        "--from-design",
        help="Path to a design doc — parses ## Breakdown hint and creates epic + stories non-interactively.",
    ),
):
    """Create a GitHub epic and update docs/focal/epics.md.

    Use --from-design <path> to parse a design doc's breakdown hint and
    create the full epic + story tree in one command.
    """
    config, _ = _load_config(require=True)

    if from_design is not None:
        from focal.pm.epic_cmd import run_from_design

        run_from_design(repo, repo_root.resolve(), config, from_design.resolve())
    else:
        from focal.pm.epic_cmd import run

        run(
            repo,
            repo_root.resolve(),
            config,
            title=title,
            description=description,
            sp=sp,
        )


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
    from focal.pm.story_cmd import run

    config, _ = _load_config(require=True)
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
    from focal.pm.plan_cmd import run

    config, _ = _load_config(require=False)
    if not config:
        typer.echo(
            "Note: no board config found — board integration will be skipped. Run: focal board setup",
            err=True,
        )

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
    from focal.pm.retro_cmd import run

    config, _ = _load_config(require=False)
    if not config:
        typer.echo(
            "Note: no board config found — board integration will be skipped. Run: focal board setup",
            err=True,
        )

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
    repo: Optional[str] = typer.Argument(
        None,
        help="Target repo (owner/repo). Omit to show status for all registered PM repos.",
    ),
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root (default: current directory). Ignored when showing all repos.",
    ),
    refresh: bool = typer.Option(
        False, "--refresh", help="Re-fetch state from GitHub before displaying status."
    ),
):
    """Print a live terminal summary of the current iteration.

    With no arguments: shows status for every repo registered via 'focal pm init',
    auto-detecting the current iteration for each.
    """
    from focal.pm.status_cmd import run

    config, _ = _load_config(require=False)
    if not config:
        typer.echo(
            "Note: no board config found — board integration will be skipped. Run: focal board setup",
            err=True,
        )

    if repo:
        run(repo, repo_root.resolve(), config, refresh=refresh)
        return

    # No repo specified — show all registered PM repos
    pm_repos = config.get("pm_repos", [])
    if not pm_repos:
        from rich.console import Console

        Console().print(
            "[yellow]No PM repos registered.[/yellow] "
            "Run [bold]focal pm init owner/repo[/bold] to register a repo."
        )
        raise typer.Exit(0)

    for entry in pm_repos:
        r = entry.get("repo", "") if isinstance(entry, dict) else str(entry)
        rr = Path(entry.get("repo_root", ".")) if isinstance(entry, dict) else Path(".")
        if not rr.exists():
            from rich.console import Console

            Console().print(f"[dim]Skipping {r} — repo_root not found: {rr}[/dim]")
            continue
        run(r, rr.resolve(), config, refresh=refresh)


@pm_app.command("velocity")
def pm_velocity(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root (default: current directory)",
    ),
):
    """Show historical velocity from retro-log.md."""
    from focal.pm import velocity_cmd

    velocity_cmd.run(repo, repo_root.resolve())


@pm_app.command("design")
def pm_design(
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root (default: current directory).",
    ),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="Filter by status: Draft, Planned, Active, Done, Archived.",
    ),
    update_index: bool = typer.Option(
        False,
        "--update-index",
        help="Regenerate docs/focal/design/INDEX.md from current design docs.",
    ),
):
    """List design docs and their lifecycle status.

    Reads docs/focal/design/D*.md, parses frontmatter, and renders a table
    grouped by lifecycle stage (Draft → Planned → Active → Done → Archived).

    Pass --update-index to regenerate INDEX.md.
    """
    from focal.pm import design_cmd

    root = repo_root.resolve()
    design_cmd.run(root, status_filter=status)
    if update_index:
        _write_design_index(root)


def _write_design_index(repo_root: Path) -> None:
    from rich.console import Console

    from focal.pm import design_cmd

    con = Console()
    docs = design_cmd.load_designs(repo_root / "docs" / "focal" / "design")
    if not docs:
        return

    status_order = design_cmd.STATUS_ORDER
    by_status: dict[str, list[dict]] = {}
    for d in docs:
        by_status.setdefault(d["status"], []).append(d)

    lines = [
        "# Design doc index",
        "",
        "<!-- Auto-generated by `focal pm design --update-index`. Do not edit manually. -->",
        "",
    ]
    for status in status_order:
        group = by_status.get(status, [])
        if not group:
            continue
        lines.append(f"## {status}")
        lines.append("")
        lines.append("| ID | Title | Epic | Updated |")
        lines.append("|---|---|---|---|")
        for d in group:
            epic_ref = (
                f"[#{d['epic']}](https://github.com/leninmehedy/focal/issues/{d['epic']})"
                if d["epic"]
                else "—"
            )
            rel_path = d["path"].name
            lines.append(
                f"| [{d['id']}]({rel_path}) | {d['title']} | {epic_ref} | {d['updated']} |"
            )
        lines.append("")

    index_path = repo_root / "docs" / "focal" / "design" / "INDEX.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    con.print(f"[green]Updated[/green] {index_path.relative_to(repo_root)}")


@pm_app.command("adopt")
def pm_adopt(
    repo: str = typer.Argument(
        ..., help="Target repo in owner/repo format (e.g. leninmehedy/focal)."
    ),
    repo_root: Path = typer.Option(
        Path("."),
        "--repo-root",
        help="Local path to the repo root. Required with --apply.",
    ),
    epic_label: str = typer.Option(
        "epic",
        "--epic-label",
        help="Comma-separated label(s) that identify epics (e.g. 'epic,feature').",
    ),
    story_label: str = typer.Option(
        "story",
        "--story-label",
        help="Comma-separated label(s) that identify stories (e.g. 'story,task').",
    ),
    sp_field: Optional[str] = typer.Option(
        None,
        "--sp-field",
        help="GitHub Projects custom field name for SP. Omit to auto-detect common names.",
    ),
    default_sp: Optional[int] = typer.Option(
        None,
        "--default-sp",
        help="Fallback SP for issues with no estimate.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Write focal-state.json. Without this flag, runs as a dry-run.",
    ),
    normalise: bool = typer.Option(
        False,
        "--normalise",
        help="Re-label issues, move SP from title to body, create sub-issue links. Requires --apply.",
    ),
    prompt_missing: bool = typer.Option(
        False,
        "--prompt-missing",
        help="Interactively prompt for SP on issues where no estimate is found.",
    ),
):
    """Scan an existing repo's issues and bootstrap Focal PM state.

    Dry-run by default — prints a discovery report without writing anything.
    Pass --apply to write focal-state.json so focal pm status/plan work immediately.
    Pass --apply --normalise to also re-format issues to Focal conventions.
    """
    if normalise and not apply:
        typer.echo("Error: --normalise requires --apply.", err=True)
        raise typer.Exit(1)

    from focal.pm import adopt_cmd

    adopt_cmd.run(
        repo=repo,
        repo_root=repo_root.resolve(),
        epic_labels=[lb.strip() for lb in epic_label.split(",")],
        story_labels=[lb.strip() for lb in story_label.split(",")],
        sp_field=sp_field,
        default_sp=default_sp,
        prompt_missing=prompt_missing,
        apply=apply,
        normalise=normalise,
    )


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
    from focal.pm.sync_state_cmd import run

    config, _ = _load_config(require=True)
    run(repo, repo_root.resolve(), config)


@cache_app.command("refresh-all")
def cache_refresh_all(
    force: bool = typer.Option(
        False, "--force", "-f", help="Ignore auto_cache_refresh flag and size limits."
    ),
):
    """Re-fetch state for all PM-managed repos registered in ~/.focal/config.json."""

    from rich.console import Console

    from focal.config import Config
    from focal.pm import pm_state
    from focal.pm.sync_state_cmd import run

    console = Console()
    config_dict, config_path = _load_config(require=True)
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

    console = Console()
    _, config_path = _load_config(require=True)
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


@pm_app.command("what-if")
def pm_what_if(
    repo: str = typer.Argument(..., help="Target repo in owner/repo format"),
    repo_root: Path = typer.Option(
        Path("."), "--repo-root", help="Local path to the repo root"
    ),
    pto: Optional[list[str]] = typer.Option(
        None,
        "--pto",
        help="PTO scenario: HANDLE:FROM:TO (e.g. alice:2026-06-02:2026-06-06). Repeatable.",
    ),
    inject: Optional[list[str]] = typer.Option(
        None,
        "--inject",
        help="Inject a high-priority story: 'TITLE:SP' (e.g. 'P1 fix:8'). Repeatable.",
    ),
    reestimate: Optional[list[str]] = typer.Option(
        None,
        "--reestimate",
        help="Re-estimate a story: STORY_ID:NEW_SP (e.g. 1.3:13). Repeatable.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Write the updated iteration-planning.md. Dry-run by default.",
    ),
):
    """Simulate what happens to the iteration plan under a hypothetical scenario.

    Dry-run by default — prints a before/after impact report without writing anything.
    Pass --apply to overwrite docs/focal/iteration-planning.md with the simulated plan.

    Examples:
      focal pm what-if owner/repo --pto alice:2026-06-02:2026-06-06
      focal pm what-if owner/repo --inject "Urgent fix:8" --reestimate 1.3:13
      focal pm what-if owner/repo --pto me:2026-06-02:2026-06-06 --apply
    """
    from focal.pm.whatif_cmd import run

    run(
        repo=repo,
        repo_root=repo_root.resolve(),
        pto_raw=pto or [],
        inject_raw=inject or [],
        reestimate_raw=reestimate or [],
        apply=apply,
    )


# focal mcp — MCP server commands
mcp_app = typer.Typer(help="MCP server for AI agent integration.")
app.add_typer(mcp_app, name="mcp")

# focal skill — agent skill installation
skill_app = typer.Typer(help="Install Focal as a skill in AI agent environments.")
app.add_typer(skill_app, name="skill")


@mcp_app.command("serve")
def mcp_serve():
    """Start the Focal MCP server (stdio transport).

    Wire it up once with: focal skill install claude
    Then any MCP-compatible agent can call Focal tools directly.
    """
    from focal.mcp_server import serve

    serve()


@skill_app.command("install")
def skill_install(
    target: str = typer.Argument(
        "auto",
        help="Agent environment to install into: claude, cursor, or auto (default).",
    ),
):
    """Install Focal as an MCP skill in an AI agent environment.

    Writes the MCP server config entry so the agent can call focal tools directly.

    Supported targets:
      claude  — writes to ~/.claude/settings.json (Claude Code)
      cursor  — writes to ~/.cursor/mcp.json (Cursor)
      auto    — detects installed agents and installs into all of them
    """
    import json

    entry = {"command": "focal", "args": ["mcp", "serve"]}
    installed: list[str] = []
    skipped: list[str] = []

    targets = []
    if target == "auto":
        if (Path.home() / ".claude").exists():
            targets.append("claude")
        if (Path.home() / ".cursor").exists():
            targets.append("cursor")
        if not targets:
            typer.echo(
                "No supported agent environments detected. "
                "Use 'focal skill install claude' or 'focal skill install cursor' explicitly."
            )
            raise typer.Exit(1)
    else:
        targets = [target.lower()]

    for t in targets:
        if t == "claude":
            settings_path = Path.home() / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            cfg: dict = {}
            if settings_path.exists():
                with open(settings_path) as f:
                    try:
                        cfg = json.load(f)
                    except json.JSONDecodeError:
                        cfg = {}
            servers = cfg.setdefault("mcpServers", {})
            if "focal" in servers:
                skipped.append("claude (already configured)")
            else:
                servers["focal"] = entry
                with open(settings_path, "w") as f:
                    json.dump(cfg, f, indent=2)
                installed.append(f"claude ({settings_path})")

        elif t == "cursor":
            mcp_path = Path.home() / ".cursor" / "mcp.json"
            mcp_path.parent.mkdir(parents=True, exist_ok=True)
            cfg = {}
            if mcp_path.exists():
                with open(mcp_path) as f:
                    try:
                        cfg = json.load(f)
                    except json.JSONDecodeError:
                        cfg = {}
            servers = cfg.setdefault("mcpServers", {})
            if "focal" in servers:
                skipped.append("cursor (already configured)")
            else:
                servers["focal"] = entry
                with open(mcp_path, "w") as f:
                    json.dump(cfg, f, indent=2)
                installed.append(f"cursor ({mcp_path})")

        else:
            typer.echo(f"Unknown target '{t}'. Supported: claude, cursor, auto.")
            raise typer.Exit(1)

    for name in installed:
        typer.echo(f"✔ Installed focal MCP skill → {name}")
    for name in skipped:
        typer.echo(f"  Already configured: {name}")

    if installed:
        typer.echo("\nRestart your agent to pick up the new skill.")
        typer.echo('Test it by asking: "List my focal design docs"')


def main() -> None:
    app()


if __name__ == "__main__":
    main()
