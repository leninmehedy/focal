"""focal pm story-create — create a story attached to an epic."""

import re
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from .. import gh
from . import pm_state

console = Console()


def _parse_epics(epics_path: Path) -> list[dict]:
    """Return list of {id, title, issue_number, sp} from docs/focal/epics.md."""
    if not epics_path.exists():
        return []
    text = epics_path.read_text()
    # Match: ## E3 — Title · [#42](url) · 21 SP
    pattern = re.compile(
        r"^## (E\d+) — (.+?) · \[#(\d+)\]\([^)]+\) · (\d+) SP",
        re.MULTILINE,
    )
    return [
        {
            "id": m.group(1),
            "title": m.group(2).strip(),
            "issue_number": int(m.group(3)),
            "sp": int(m.group(4)),
        }
        for m in pattern.finditer(text)
    ]


def _next_story_id(epics_path: Path, epic_id: str) -> str:
    """Return next story ID under the given epic (e.g. '3.4')."""
    text = epics_path.read_text()
    epic_num = int(epic_id[1:])
    # Find story rows like | **3.1** — ... | or | **3.2** — ... |
    pattern = re.compile(rf"\|\s*\*\*{epic_num}\.(\d+)\*\*")
    existing = [int(m.group(1)) for m in pattern.finditer(text)]
    next_num = max(existing, default=0) + 1
    return f"{epic_num}.{next_num}"


def _append_story_row(
    epics_path: Path,
    epic_id: str,
    story_id: str,
    title: str,
    issue_number: int,
    repo: str,
    sp: int,
) -> None:
    """Append a story row to the epic's table in docs/focal/epics.md."""
    text = epics_path.read_text()
    row = (
        f"| **{story_id}** — {title} "
        f"| [#{issue_number}](https://github.com/{repo}/issues/{issue_number}) "
        f"| {sp} |\n"
    )
    # Insert after the table header of the matching epic
    # Find the |---|---|---| line that belongs to this epic
    header_pattern = re.compile(rf"(## {epic_id} —.*?\|---\|---\|---\|\n)", re.DOTALL)
    m = header_pattern.search(text)
    if m:
        insert_pos = m.end()
        text = text[:insert_pos] + row + text[insert_pos:]
        epics_path.write_text(text)
    else:
        # Fallback: append at end of file
        with open(epics_path, "a") as f:
            f.write(row)


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


def run(repo: str, repo_root: Path, config: dict) -> None:
    """Interactive wizard — create a GitHub story and update docs/focal/epics.md."""
    console.print(f"\n[bold cyan]  ◎  Focal — story create ({repo})[/bold cyan]\n")

    epics_path = repo_root / "docs" / "focal" / "epics.md"
    if not epics_path.exists():
        console.print(
            "[red]docs/focal/epics.md not found. Run [bold]focal pm init[/bold] first.[/red]"
        )
        return

    # Prefer state cache; fall back to parsing epics.md
    state = pm_state.load(repo_root)
    state["repo"] = repo
    epics = state["epics"] if state["epics"] else _parse_epics(epics_path)
    if not epics:
        console.print(
            "[red]No epics found. Run [bold]focal pm epic-create[/bold] first.[/red]"
        )
        return

    # Select epic
    console.print("Select epic:\n")
    for i, e in enumerate(epics, 1):
        console.print(
            f"  [bold]{i}[/bold]  {e['id']} — {e['title']} (#{e['issue_number']}) · {e['sp']} SP"
        )
    choice = Prompt.ask("\nChoice", default="1")
    try:
        epic = epics[int(choice) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid choice.[/red]")
        return

    story_id = _next_story_id(epics_path, epic["id"])
    console.print(f"\nNext story ID: [bold]{story_id}[/bold]\n")

    title = Prompt.ask("Story title")
    description = Prompt.ask("Description (one line)")
    sp_raw = Prompt.ask("Estimate (story points)", default="0")
    try:
        sp = int(sp_raw)
    except ValueError:
        sp = 0

    assignee = config.get("assignee", "")
    board_number = config.get("board_number")
    board_owner = config.get("board_owner", "")

    body = (
        f"Part of epic #{epic['issue_number']}.\n\n"
        f"{description}\n\n"
        f"**Estimated:** {sp} SP"
    )

    # Create GitHub issue
    console.print("\nCreating GitHub issue...")
    try:
        issue = gh.create_issue(
            repo=repo,
            title=title,
            body=body,
            labels=["story"],
            assignee=assignee,
        )
    except RuntimeError as e:
        console.print(f"[red]Failed to create issue: {e}[/red]")
        return

    issue_number = issue["number"]
    issue_url = issue["url"]
    console.print(f"  [green]✔[/green] Created issue #{issue_number} — {title}")

    # Link as sub-issue to epic
    console.print("Linking as sub-issue to epic...")
    try:
        gh.link_sub_issue(repo, epic["issue_number"], issue["id"])
        console.print(f"  [green]✔[/green] Linked to epic #{epic['issue_number']}")
    except RuntimeError as e:
        console.print(f"  [yellow]⚠[/yellow]  Sub-issue link failed: {e}")

    # Add to project board and set SP
    if board_number and board_owner:
        console.print("Adding to project board...")
        try:
            item_id = gh.add_item_get_id(board_number, board_owner, issue_url)
            console.print(f"  [green]✔[/green] Added to board #{board_number}")

            estimate_field_id = config.get("estimate_field_id")
            if estimate_field_id and sp > 0:
                pid = gh.project_id(board_number, board_owner)
                gh.set_item_number_field(pid, item_id, estimate_field_id, sp)
                console.print(f"  [green]✔[/green] Estimate set: {sp} SP")
        except RuntimeError as e:
            console.print(f"  [yellow]⚠[/yellow]  Board update failed: {e}")

    # Update docs/focal/epics.md
    _append_story_row(epics_path, epic["id"], story_id, title, issue_number, repo, sp)
    console.print(f"  [green]✔[/green] docs/focal/epics.md updated ({story_id})")

    # Update local state cache
    pm_state.upsert_story(
        state,
        epic["id"],
        {
            "id": story_id,
            "title": title,
            "issue_number": issue_number,
            "issue_url": issue_url,
            "issue_db_id": issue["id"],
            "sp": sp,
            "assignee": assignee,
            "status": "open",
            "project_status": "",
        },
    )
    pm_state.save(repo_root, state)
    console.print("  [green]✔[/green] Local state updated")

    # Commit
    _git_commit(repo_root, f"chore: add story {story_id} — {title} to epics.md")
    console.print("  [green]✔[/green] Committed")

    console.print(f"\n[bold green]Story {story_id} created![/bold green]")
    console.print(f"  GitHub:  {issue_url}")
    console.print(f"  Epic:    #{epic['issue_number']} {epic['title']}")
