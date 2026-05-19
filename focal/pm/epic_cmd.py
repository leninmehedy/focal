"""focal pm epic create — guided wizard to create a GitHub epic."""

import re
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from .. import gh
from . import pm_state

console = Console()


def _next_epic_id(epics_path: Path) -> str:
    """Return the next epic ID (E1, E2, …) based on existing entries in epics.md."""
    if not epics_path.exists():
        return "E1"
    text = epics_path.read_text()
    ids = re.findall(r"^## (E\d+) —", text, re.MULTILINE)
    if not ids:
        return "E1"
    last = max(int(e[1:]) for e in ids)
    return f"E{last + 1}"


def _append_epic(
    epics_path: Path,
    epic_id: str,
    title: str,
    description: str,
    issue_number: int,
    repo: str,
    sp: int,
) -> None:
    """Append a new epic entry to docs/epics.md."""
    entry = (
        f"\n## {epic_id} — {title} · "
        f"[#{issue_number}](https://github.com/{repo}/issues/{issue_number}) · {sp} SP\n"
        f"\n{description}\n"
        f"\n| Story | GitHub | SP |\n"
        f"|---|---|---|\n"
    )
    with open(epics_path, "a") as f:
        f.write(entry)


def _git_commit(repo_root: Path, message: str) -> None:
    subprocess.run(
        ["git", "add", "docs/focal/epics.md"],
        cwd=repo_root,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        capture_output=True,
    )


def run(
    repo: str,
    repo_root: Path,
    config: dict,
    title: str | None = None,
    description: str | None = None,
    sp: int | None = None,
) -> None:
    """Create a GitHub epic and update docs/focal/epics.md."""
    console.print(f"\n[bold cyan]  ◎  Focal — epic create ({repo})[/bold cyan]\n")

    epics_path = repo_root / "docs" / "focal" / "epics.md"
    if not epics_path.exists():
        console.print(
            "[red]docs/epics.md not found. Run [bold]focal pm init[/bold] first.[/red]"
        )
        return

    epic_id = _next_epic_id(epics_path)
    console.print(f"Next epic ID: [bold]{epic_id}[/bold]\n")

    if title is None:
        title = Prompt.ask("Epic title")
    if description is None:
        description = Prompt.ask("Description (one line)")
    if sp is None:
        sp_raw = Prompt.ask("Estimate (story points)", default="0")
        try:
            sp = int(sp_raw)
        except ValueError:
            sp = 0

    assignee = config.get("assignee", "")
    board_number = config.get("board_number")
    board_owner = config.get("board_owner", "")

    body = (
        f"## Vision\n\n{description}\n\n"
        "## Stories\n\n<!-- Stories will be added here as sub-issues -->\n\n"
        "## Acceptance criteria\n\n<!-- What must be true for this epic to be done? -->"
    )

    # Create GitHub issue
    console.print("\nCreating GitHub issue...")
    try:
        issue = gh.create_issue(
            repo=repo,
            title=f"Epic: {title}",
            body=body,
            labels=["epic"],
            assignee=assignee,
        )
    except RuntimeError as e:
        console.print(f"[red]Failed to create issue: {e}[/red]")
        return

    issue_number = issue["number"]
    issue_url = issue["url"]
    console.print(f"  [green]✔[/green] Created issue #{issue_number} — Epic: {title}")

    # Add to project board
    if board_number and board_owner:
        console.print("Adding to project board...")
        try:
            item_id = gh.add_item_get_id(board_number, board_owner, issue_url)
            console.print(f"  [green]✔[/green] Added to board #{board_number}")

            # Set story points if Estimate field is configured
            estimate_field_id = config.get("estimate_field_id")
            if estimate_field_id and sp > 0:
                pid = gh.project_id(board_number, board_owner)
                gh.set_item_number_field(pid, item_id, estimate_field_id, sp)
                console.print(f"  [green]✔[/green] Estimate set: {sp} SP")
        except RuntimeError as e:
            console.print(f"  [yellow]⚠[/yellow]  Board update failed: {e}")

    # Update docs/focal/epics.md
    _append_epic(epics_path, epic_id, title, description, issue_number, repo, sp)
    console.print(f"  [green]✔[/green] docs/focal/epics.md updated ({epic_id})")

    # Update local state cache
    state = pm_state.load(repo_root)
    state["repo"] = repo
    pm_state.upsert_epic(
        state,
        {
            "id": epic_id,
            "title": title,
            "issue_number": issue_number,
            "issue_url": issue_url,
            "issue_db_id": issue["id"],
            "sp": sp,
            "status": "open",
        },
    )
    pm_state.save(repo_root, state)
    console.print("  [green]✔[/green] Local state updated")

    # Commit
    _git_commit(repo_root, f"chore: add {epic_id} — {title} to epics.md")
    console.print("  [green]✔[/green] Committed")

    console.print(f"\n[bold green]Epic {epic_id} created![/bold green]")
    console.print(f"  GitHub: {issue_url}")
    console.print(f"  Next:   [bold]focal pm story-create {repo}[/bold]")
