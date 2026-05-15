"""Interactive setup wizard — guides a new user through configuring Focal."""

import re
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from . import gh
from .config import Config

console = Console()


# ── Prerequisite checks ───────────────────────────────────────────────────────


def _check_prerequisites() -> bool:
    console.rule("[bold]Step 1: Checking prerequisites[/bold]")
    ok = True

    # gh installed?
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        console.print(f"[green]✔[/green] {result.stdout.splitlines()[0]}")
    except FileNotFoundError:
        console.print("[red]✖[/red] gh CLI not found. Install: https://cli.github.com")
        return False

    # gh authenticated?
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    combined = result.stdout + result.stderr
    if result.returncode != 0:
        console.print("[red]✖[/red] gh not authenticated. Run: gh auth login")
        return False

    if "project" not in combined:
        console.print(
            "[yellow]⚠[/yellow]  'project' scope may be missing. "
            "Run: gh auth refresh -s project"
        )
        ok = False
    else:
        console.print("[green]✔[/green] gh authenticated with project scope")

    console.print(f"[green]✔[/green] Python {sys.version.split()[0]}")
    return ok


# ── Board URL parsing ─────────────────────────────────────────────────────────


def _parse_board_url(url: str) -> tuple[str, int]:
    m = re.match(
        r"https://github\.com/(?:users|orgs)/([^/]+)/projects/(\d+)", url.strip()
    )
    if not m:
        raise ValueError(
            "Could not parse board URL. Expected format: "
            "https://github.com/users/USERNAME/projects/NUMBER"
        )
    return m.group(1), int(m.group(2))


# ── Repo selection ────────────────────────────────────────────────────────────


def _select_repos() -> list[str]:
    console.rule("[bold]Step 3: Select repos to sync[/bold]")
    console.print("How would you like to select repos?\n")
    console.print("  [bold]1[/bold]  Manual list — type repos one by one (owner/repo)")
    console.print("  [bold]2[/bold]  Interactive select — browse your accessible repos")
    console.print("  [bold]3[/bold]  Full scan — all accessible repos (may be slow)\n")

    choice = Prompt.ask("Choice", choices=["1", "2", "3"])

    if choice == "1":
        console.print("\nEnter repos one per line (owner/repo). Empty line to finish:")
        repos = []
        while True:
            r = Prompt.ask("  Repo", default="")
            if not r:
                break
            if "/" not in r:
                console.print(
                    "[yellow]  Format must be owner/repo — try again[/yellow]"
                )
                continue
            repos.append(r.strip())
        return repos

    # Choices 2 and 3: list repos from gh
    limit = "100" if choice == "2" else "1000"
    if choice == "3":
        console.print(
            "\n[yellow]Scanning all accessible repos (may take a minute)...[/yellow]"
        )

    raw = subprocess.run(
        [
            "gh",
            "repo",
            "list",
            "--limit",
            limit,
            "--json",
            "nameWithOwner",
            "--jq",
            ".[].nameWithOwner",
        ],
        capture_output=True,
        text=True,
    )
    all_repos = [r.strip() for r in raw.stdout.splitlines() if r.strip()]
    if not all_repos:
        console.print("[red]No repos found.[/red]")
        return []

    console.print(
        f"\nFound [bold]{len(all_repos)}[/bold] repos. Enter numbers to select (comma-separated):\n"
    )
    for i, r in enumerate(all_repos, 1):
        console.print(f"  [dim]{i:4}.[/dim]  {r}")

    selection = Prompt.ask("\nSelection")
    repos = []
    for s in selection.split(","):
        try:
            repos.append(all_repos[int(s.strip()) - 1])
        except (ValueError, IndexError):
            pass
    return repos


# ── Status column inspection ──────────────────────────────────────────────────


def _inspect_status_columns(
    repos: list[str],
    personal_options: list[dict],
    status_map: dict,
) -> dict:
    """
    Compare each repo's origin project Status options against the personal board.
    Offers to fix mismatches; builds status_map entries for anything it can't fix.
    Returns updated status_map.
    """
    console.rule("[bold]Step 4: Inspecting Status columns[/bold]")
    personal_names = {o["name"] for o in personal_options}

    for repo in repos:
        # Find projects for this repo
        raw = subprocess.run(
            [
                "gh",
                "project",
                "list",
                "--owner",
                repo.split("/")[0],
                "--format",
                "json",
                "--jq",
                f'[.projects[] | select(.url | contains("{repo}"))]',
            ],
            capture_output=True,
            text=True,
        )
        try:
            projects = [p for p in __import__("json").loads(raw.stdout or "[]")]
        except Exception:
            projects = []

        for project in projects:
            pid = project.get("id", "")
            title = project.get("title", repo)
            field = gh.origin_status_field(pid) if pid else None
            if not field:
                continue
            origin_names = {o["name"] for o in field.get("options", [])}
            missing = personal_names - origin_names
            extra = origin_names - personal_names

            if not missing and not extra:
                console.print(f"[green]✔[/green] '{title}' — Status columns match")
                continue

            console.print(f"\n[yellow]⚠[/yellow]  '{title}' has mismatches:")
            if missing:
                console.print(f"   Missing in origin: {', '.join(sorted(missing))}")
            if extra:
                console.print(f"   Extra in origin:   {', '.join(sorted(extra))}")

            # Build status_map entries for extra origin statuses
            for name in extra:
                if pid not in status_map:
                    status_map[pid] = {}
                # Ask which personal option this maps to
                choices = [o["name"] for o in personal_options]
                console.print(
                    f"\n   Map origin status '[bold]{name}[/bold]' to personal board option:"
                )
                for i, c in enumerate(choices, 1):
                    console.print(f"     {i}. {c}")
                sel = Prompt.ask("   Choice (enter number, or skip)", default="")
                if sel.isdigit() and 1 <= int(sel) <= len(choices):
                    status_map[pid][name] = choices[int(sel) - 1]

    return status_map


# ── Main wizard ───────────────────────────────────────────────────────────────


def _manage_existing(focal_home: Path, config_path: Path) -> None:
    """Handle re-runs when config.json already exists."""
    cfg = Config.load(config_path)

    console.print("\n[bold yellow]Focal is already configured.[/bold yellow]")
    console.print(
        f"  Board:  https://github.com/users/{cfg.board_owner}/projects/{cfg.board_number}"
    )
    console.print(f"  Repos:  {len(cfg.repos)} tracked\n")
    for r in cfg.repos:
        console.print(f"    • {r}")

    console.print("\nWhat would you like to do?\n")
    console.print("  [bold]1[/bold]  Add repos to the existing config")
    console.print("  [bold]2[/bold]  Edit repo list (add or remove)")
    console.print("  [bold]3[/bold]  Full reconfigure (replaces everything)")
    console.print("  [bold]4[/bold]  Cancel\n")

    choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="1")

    if choice == "4":
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit(0)

    if choice == "3":
        if not Confirm.ask(
            "[bold red]This will overwrite your entire config. Proceed?[/bold red]",
            default=False,
        ):
            raise typer.Exit(0)
        return  # fall through to full setup

    if choice == "1":
        console.print(
            "\n[bold]Add repos[/bold] — enter new repos to track (one per line, blank to finish):\n"
        )
        added = []
        while True:
            r = Prompt.ask("Repo (owner/repo)", default="").strip()
            if not r:
                break
            if r in cfg.repos:
                console.print(f"  [yellow]Already tracked:[/yellow] {r}")
            else:
                cfg.repos.append(r)
                added.append(r)
                console.print(f"  [green]✔[/green] Added: {r}")
        if not added:
            console.print("[dim]Nothing added.[/dim]")
            raise typer.Exit(0)

    elif choice == "2":
        console.print("\n[bold]Edit repo list[/bold]\n")
        repos = list(cfg.repos)
        for i, r in enumerate(repos, 1):
            console.print(f"  [bold]{i}[/bold]  {r}")
        console.print(
            "\nEnter numbers to [red]remove[/red] (comma-separated), or blank to skip:"
        )
        raw = Prompt.ask("Remove", default="").strip()
        if raw:
            to_remove = set()
            for part in raw.split(","):
                try:
                    to_remove.add(int(part.strip()) - 1)
                except ValueError:
                    pass
            cfg.repos = [r for i, r in enumerate(repos) if i not in to_remove]
            removed = [repos[i] for i in to_remove if i < len(repos)]
            for r in removed:
                console.print(f"  [red]✖[/red] Removed: {r}")

        console.print("\nEnter new repos to add (one per line, blank to finish):")
        while True:
            r = Prompt.ask("Repo (owner/repo)", default="").strip()
            if not r:
                break
            if r in cfg.repos:
                console.print(f"  [yellow]Already tracked:[/yellow] {r}")
            else:
                cfg.repos.append(r)
                console.print(f"  [green]✔[/green] Added: {r}")

    cfg.save(config_path)
    console.print(f"\n[green]✔[/green] config.json updated ({len(cfg.repos)} repos)")
    console.print("\nRun a sync to apply: [bold]python3 focal.py board sync[/bold]")
    raise typer.Exit(0)


def run(focal_home: Path) -> None:
    console.print("\n[bold cyan]  ◎  Focal Setup Wizard[/bold cyan]\n")

    focal_home.mkdir(parents=True, exist_ok=True)
    config_path = focal_home / "config.json"
    if config_path.exists():
        _manage_existing(focal_home, config_path)
        # Only reaches here if choice == "3" (full reconfigure)

    if not _check_prerequisites():
        raise typer.Exit(1)

    # Board URL
    console.rule("[bold]Step 2: Personal board[/bold]")
    while True:
        url = Prompt.ask(
            "Personal board URL",
            default="https://github.com/users/YOUR_USERNAME/projects/NUMBER",
        )
        try:
            board_owner, board_number = _parse_board_url(url)
            break
        except ValueError as e:
            console.print(f"[red]{e}[/red]")

    assignee = Prompt.ask("Your GitHub username (assignee filter)", default=board_owner)
    done_status = Prompt.ask("Exact name of your Done status column", default="✅ Done")

    # Fetch Status field from personal board
    console.print(f"\nFetching Status field from board #{board_number}...")
    try:
        fields = gh.project_fields(board_number, board_owner)
    except RuntimeError as e:
        console.print(f"[red]Could not fetch board fields: {e}[/red]")
        raise typer.Exit(1)

    status_field = next((f for f in fields if f.get("name") == "Status"), None)
    if not status_field:
        console.print(
            "[red]No 'Status' single-select field found on your board.[/red]\n"
            "Add one at: https://github.com/users/{board_owner}/projects/{board_number}"
        )
        raise typer.Exit(1)

    status_field_id = status_field["id"]
    personal_options = status_field.get("options", [])
    console.print(
        f"[green]✔[/green] Status field found with {len(personal_options)} options: "
        + ", ".join(o["name"] for o in personal_options)
    )

    # Repo selection
    repos = _select_repos()
    if not repos:
        console.print("[red]No repos selected — exiting.[/red]")
        raise typer.Exit(1)
    console.print(f"\n[green]✔[/green] {len(repos)} repo(s) selected")

    # Status column inspection (optional)
    status_map: dict = {}
    if Confirm.ask(
        "\nInspect and align Status columns across origin projects?", default=True
    ):
        status_map = _inspect_status_columns(repos, personal_options, status_map)
        if status_map:
            import json

            sm_path = focal_home / "status_map.json"
            with open(sm_path, "w") as f:
                json.dump(status_map, f, indent=2)
            console.print(f"[green]✔[/green] Written: {sm_path}")

    # Write config.json
    console.rule("[bold]Writing config[/bold]")
    cfg = Config(
        board_owner=board_owner,
        board_number=board_number,
        assignee=assignee,
        status_field_id=status_field_id,
        done_status=done_status,
        repos=repos,
    )
    cfg.save(config_path)
    console.print(f"[green]✔[/green] Written: {config_path}")

    console.print("\n[bold green]Setup complete![/bold green]\n")
    console.print("Next steps:")
    console.print("  Run a one-off sync:  [bold]python3 focal.py sync[/bold]")
    console.print(
        "  Follow logs:         [bold]tail -f ~/.focal/logs/$(date '+%Y-%m-%d').log[/bold]"
    )
