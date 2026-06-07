"""focal init — bootstrap a repo with Focal project management structure."""

import importlib.resources
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from focal.config import Config

console = Console()

# Resolve templates from inside the installed package (works with pip/pipx and local dev)
_pkg_templates = importlib.resources.files("focal") / "templates"
TEMPLATES_DIR = Path(str(_pkg_templates))

LABELS = [
    ("epic", "5319E7", "Large feature — parent of stories"),
    ("story", "0075CA", "A single deliverable unit of work, child of an epic"),
]

CANONICAL_STATUS_COLUMNS = [
    "🆕 New",
    "📋 Backlog",
    "🔖 Ready",
    "🏗 In progress",
    "✋ Blocked",
    "👀 In review",
    "✅ Done",
]

GENERAL_MAINTENANCE_BODY = """\
## Purpose

Catch-all epic for unplanned work: bug fixes, dependency updates, hotfixes, and
any task that arrives outside of iteration planning.

**Every task needs a GitHub issue.** If a bug or urgent work doesn't belong to a
planned epic, create a story under this epic rather than working without a ticket.

## When to use E0

- Bug reports raised by users or CI
- Security patches and dependency upgrades
- Housekeeping tasks (CI config, docs, tooling)
- Any work injected mid-iteration that doesn't fit a planned epic

## Stories

<!-- Stories will be added here as sub-issues -->

## Notes

E0 is permanent and intentionally open. It is never completed — ongoing
maintenance work always has a home here.
"""


def _gh(*args: str) -> tuple[int, str, str]:
    result = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _ensure_label(repo: str, name: str, color: str, description: str) -> None:
    _, out, _ = _gh(
        "label",
        "list",
        "--repo",
        repo,
        "--json",
        "name",
        "--jq",
        f'[.[].name] | contains(["{name}"])',
    )
    if out == "true":
        console.print(f"  [dim]label '{name}' already exists — skipping[/dim]")
        return
    rc, _, err = _gh(
        "label",
        "create",
        name,
        "--repo",
        repo,
        "--color",
        color,
        "--description",
        description,
        "--force",
    )
    if rc != 0:
        console.print(f"  [yellow]⚠[/yellow]  Could not create label '{name}': {err}")
    else:
        console.print(f"  [green]✔[/green] Label '{name}' ready")


def _copy_template(src: Path, dest: Path, repo: str) -> None:
    if dest.exists():
        console.print(
            f"  [dim]{dest.relative_to(dest.anchor)} already exists — skipping[/dim]"
        )
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text().replace("{repo}", repo)
    dest.write_text(content)
    console.print(f"  [green]✔[/green] {dest}")


def _validate_repo_root(repo: str, repo_root: Path) -> None:
    """Exit with a clear message if repo_root is not a usable local repo directory."""
    import os

    import typer

    if not repo_root.exists() or not repo_root.is_dir():
        console.print(
            f"\n[red]Error:[/red] {repo_root} is not a directory.\n\n"
            f"Run this command from inside your local clone of [bold]{repo}[/bold], "
            "or pass [bold]--repo-root /path/to/clone[/bold]."
        )
        raise typer.Exit(1)

    if not os.access(repo_root, os.W_OK):
        console.print(
            f"\n[red]Error:[/red] No write permission to {repo_root}.\n\n"
            f"Run this command from inside your local clone of [bold]{repo}[/bold], "
            "or pass [bold]--repo-root /path/to/clone[/bold]."
        )
        raise typer.Exit(1)

    if not (repo_root / ".git").exists():
        console.print(
            f"[yellow]Warning:[/yellow] {repo_root} does not appear to be a git repository. "
            "Continuing — commit the scaffold manually when done.\n"
        )


def _ensure_general_maintenance_epic(repo: str, repo_root: Path, config: dict) -> None:
    """Create the E0 General Maintenance epic if it doesn't already exist (idempotent)."""
    from . import pm_state

    epics_path = repo_root / "docs" / "focal" / "epics.md"
    if not epics_path.exists():
        console.print("  [dim]epics.md not found — skipping E0 creation[/dim]")
        return

    # Idempotent — skip if E0 already present
    text = epics_path.read_text()
    if re.search(r"^## E0 —", text, re.MULTILINE):
        console.print("  [dim]E0 General Maintenance already exists — skipping[/dim]")
        return

    console.print("Creating E0 General Maintenance epic on GitHub...")
    try:
        from .. import gh

        issue = gh.create_issue(
            repo=repo,
            title="General Maintenance",
            body=GENERAL_MAINTENANCE_BODY,
            labels=["epic"],
            assignee="",
        )
    except RuntimeError as e:
        console.print(f"  [yellow]⚠[/yellow]  Could not create E0 epic: {e}")
        return

    issue_number = issue["number"]
    issue_url = issue["url"]

    # Prepend E0 entry at the top of epics.md so it always appears first
    entry = (
        f"\n## E0 — General Maintenance · "
        f"[#{issue_number}](https://github.com/{repo}/issues/{issue_number}) · 0 SP\n"
        "\nCatch-all for bugs, hotfixes, and unplanned work. "
        "Every task needs an issue — use E0 when work doesn't belong to a planned epic.\n"
        "\n| Story | GitHub | SP |\n"
        "|---|---|---|\n"
    )
    lines = text.splitlines(keepends=True)
    # Insert after the first heading line
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_at = i + 1
            break
    lines.insert(insert_at, entry)
    epics_path.write_text("".join(lines))

    console.print(
        f"  [green]✔[/green] E0 General Maintenance created (#{issue_number})"
    )

    # Update state cache
    state = pm_state.load(repo_root)
    state["repo"] = repo
    pm_state.upsert_epic(
        state,
        {
            "id": "E0",
            "title": "General Maintenance",
            "issue_number": issue_number,
            "issue_url": issue_url,
            "issue_db_id": issue["id"],
            "sp": 0,
            "status": "open",
            "stories": [],
        },
    )
    pm_state.save(repo_root, state)
    console.print("  [green]✔[/green] Local state updated")

    # Add to board if configured
    board_number = config.get("board_number")
    board_owner = config.get("board_owner", "")
    if board_number and board_owner:
        try:
            from .. import gh

            gh.add_item_get_id(board_number, board_owner, issue_url)
            console.print(f"  [green]✔[/green] Added to board #{board_number}")
        except RuntimeError as e:
            console.print(f"  [yellow]⚠[/yellow]  Board update skipped: {e}")


def run(
    repo: str,
    repo_root: Path,
    config: "Config | None" = None,
    config_path: "Path | None" = None,
) -> None:
    """Bootstrap repo with Focal project management structure."""
    console.print(f"\n[bold cyan]  ◎  Focal Init — {repo}[/bold cyan]\n")

    _validate_repo_root(repo, repo_root)

    # ── Labels ────────────────────────────────────────────────────────────────
    console.rule("[bold]Step 1: GitHub labels[/bold]")
    for name, color, desc in LABELS:
        _ensure_label(repo, name, color, desc)

    # ── Issue templates ───────────────────────────────────────────────────────
    console.rule("[bold]Step 2: Issue templates[/bold]")
    for tmpl in (TEMPLATES_DIR / "ISSUE_TEMPLATE").iterdir():
        _copy_template(tmpl, repo_root / ".github" / "ISSUE_TEMPLATE" / tmpl.name, repo)

    # ── Docs scaffold ─────────────────────────────────────────────────────────
    console.rule("[bold]Step 3: Docs scaffold[/bold]")
    for tmpl in ("epics.md", "plan.md", "iteration-planning.md", "retro-log.md"):
        _copy_template(TEMPLATES_DIR / tmpl, repo_root / "docs" / "focal" / tmpl, repo)

    design_dir = repo_root / "docs" / "focal" / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    _copy_template(
        TEMPLATES_DIR / "design" / "design-template.md",
        design_dir / "design-template.md",
        repo,
    )
    console.print(f"  [green]✔[/green] {design_dir}/")

    # Register in ~/.focal/config.json pm_repos so cache refresh-all can find this repo
    if config is not None and config_path is not None:
        if config.register_pm_repo(repo, repo_root):
            config.save(config_path)
            console.print(
                "  [green]✔[/green] Registered in config (focal cache refresh-all will include this repo)"
            )

    # ── General Maintenance epic (E0) ─────────────────────────────────────────
    console.rule("[bold]Step 4: General Maintenance epic (E0)[/bold]")
    _ensure_general_maintenance_epic(
        repo, repo_root, config.__dict__ if config is not None else {}
    )

    console.print("\n[bold green]Init complete![/bold green]\n")

    no_board = config is None
    if no_board:
        console.print(
            "[bold yellow]⚠  No board configured yet.[/bold yellow]  "
            "Run [bold]focal board setup[/bold] to connect a GitHub Projects board — "
            "epics and stories won't appear on your board until you do.\n"
        )

    console.print("Next steps:")
    step = 1
    if no_board:
        console.print("  0. Create your project board:  [bold]focal board setup[/bold]")
    console.print(
        f"  {step}. Write your plan:        [bold]edit docs/focal/plan.md[/bold]"
    )
    step += 1
    console.print(
        f"  {step}. Adopt the plan:         [bold]focal pm adopt-plan {repo}[/bold]"
        "  (dry-run first, then --apply)"
    )
    step += 1
    console.print(
        f"  {step}. Commit the scaffold:    [bold]git add docs/focal/ .github/ISSUE_TEMPLATE/ && "
        "git commit -m 'chore: focal init'[/bold]"
    )
    console.print("\nCanonical Status columns for your GitHub Projects board:")
    for col in CANONICAL_STATUS_COLUMNS:
        console.print(f"  {col}")
