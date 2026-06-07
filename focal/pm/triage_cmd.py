"""focal pm triage — surface open issues not tracked in any epic."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .. import gh
from . import pm_state

console = Console()


def _age(created_at: str) -> str:
    """Return human-readable age string from ISO-8601 timestamp."""
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        days = delta.days
        if days == 0:
            hours = delta.seconds // 3600
            return f"{hours}h" if hours > 0 else "<1h"
        return f"{days}d"
    except Exception:
        return "?"


def run(
    repo: str,
    repo_root: Path,
    *,
    label: str | None = None,
    unassigned: bool = False,
    days: int | None = None,
    as_json: bool = False,
) -> None:
    state = pm_state.load(repo_root)

    # Collect all issue numbers tracked in focal state
    tracked: set[int] = set()
    for epic in state.get("epics", []):
        if epic.get("issue_number"):
            tracked.add(epic["issue_number"])
        for story in epic.get("stories", []):
            if story.get("issue_number"):
                tracked.add(story["issue_number"])

    # Fetch open issues from GitHub
    try:
        issues = gh.open_issues(repo)
    except RuntimeError as e:
        console.print(f"[red]Error fetching issues:[/red] {e}")
        raise SystemExit(1)

    # Subtract tracked issues
    untracked = [i for i in issues if i["number"] not in tracked]

    # Apply --label filter
    if label:
        untracked = [i for i in untracked if label in i["labels"]]

    # Apply --unassigned filter
    if unassigned:
        untracked = [i for i in untracked if not i["assignees"]]

    # Apply --days filter
    if days is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        untracked = [
            i
            for i in untracked
            if datetime.fromisoformat(
                i["created_at"].replace("Z", "+00:00")
            ).timestamp()
            >= cutoff
        ]

    if as_json:
        print(json.dumps(untracked, indent=2))
        return

    console.print()
    console.print(f"  [bold cyan]◎  Focal — triage ({repo})[/bold cyan]")
    console.print()

    if not untracked:
        console.print(
            "  [green]✓ No untracked issues — everything is linked to an epic.[/green]"
        )
        console.print()
        return

    console.print(
        f"  [yellow]{len(untracked)} untracked issue{'s' if len(untracked) != 1 else ''} (not linked to any epic)[/yellow]"
    )
    console.print()

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Labels", style="dim")
    table.add_column("Assignee", style="dim")
    table.add_column("Age", style="dim", no_wrap=True)

    for issue in untracked:
        labels_str = ", ".join(issue["labels"]) if issue["labels"] else "—"
        assignee_str = ", ".join(issue["assignees"]) if issue["assignees"] else "—"
        age_str = _age(issue["created_at"])
        table.add_row(
            str(issue["number"]),
            issue["title"],
            labels_str,
            assignee_str,
            age_str,
        )

    console.print(table)
    console.print()
    console.print(
        "  [dim]Next step: run[/dim] focal pm story-create "
        f'{repo} --epic E0 --title "..." [dim]to track any of these.[/dim]'
    )
    console.print()
