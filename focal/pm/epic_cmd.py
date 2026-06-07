"""focal pm epic create — guided wizard to create a GitHub epic."""

import re
import subprocess
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from .. import gh
from . import epics_renderer, pm_state

console = Console()


def _next_epic_id(epics_path: Path) -> str:
    """Return the next epic ID (E1, E2, …) based on existing entries in epics.md.

    E0 is reserved for the General Maintenance epic created by `focal pm init`.
    User epics always start at E1.
    """
    if not epics_path.exists():
        return "E1"
    text = epics_path.read_text()
    ids = re.findall(r"^## (E\d+) —", text, re.MULTILINE)
    # Exclude E0 — it's the reserved General Maintenance epic
    user_ids = [int(e[1:]) for e in ids if e != "E0"]
    if not user_ids:
        return "E1"
    return f"E{max(user_ids) + 1}"


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

    # Re-render epics.md from state
    epics_renderer.render(repo_root, state)
    console.print(f"  [green]✔[/green] docs/focal/epics.md updated ({epic_id})")

    # Commit
    _git_commit(repo_root, f"chore: add {epic_id} — {title} to epics.md")
    console.print("  [green]✔[/green] Committed")

    console.print(f"\n[bold green]Epic {epic_id} created![/bold green]")
    console.print(f"  GitHub: {issue_url}")
    console.print(f"  Next:   [bold]focal pm story-create {repo}[/bold]")

    return issue_number, issue["id"]


def run_from_design(
    repo: str,
    repo_root: Path,
    config: dict,
    design_path: Path,
) -> None:
    """Create an epic + full story tree from a design doc's ## Breakdown hint."""
    from .breakdown_parser import parse as parse_breakdown
    from .design_cmd import rewrite_frontmatter

    console.print(
        f"\n[bold cyan]  ◎  Focal — epic create from design ({repo})[/bold cyan]\n"
    )

    if not design_path.exists():
        console.print(f"[red]Design doc not found: {design_path}[/red]")
        return

    # Parse frontmatter
    from .design_cmd import _parse_frontmatter

    fm = _parse_frontmatter(design_path)
    if not fm:
        console.print("[red]No frontmatter found in design doc.[/red]")
        return

    doc_id = fm.get("id", design_path.stem)
    doc_status = fm.get("status", "")

    # Parse breakdown
    breakdown = parse_breakdown(design_path)
    if breakdown is None:
        console.print(
            f"[red]No '## Breakdown hint' section found in {design_path.name}.[/red]"
        )
        return

    # Dry-run summary
    console.print(f"Design doc:  [bold]{doc_id}[/bold] — {fm.get('title', '')}")
    console.print(f"Status:      {doc_status}\n")
    console.print(
        f"[bold]Epic to create:[/bold]  {breakdown['epic_title']}  ({breakdown['epic_sp']} SP)"
    )
    if breakdown["stories"]:
        console.print(
            f"\n[bold]Stories to create ({len(breakdown['stories'])}):[/bold]"
        )
        for s in breakdown["stories"]:
            console.print(f"  · {s['title']}  ({s['sp']} SP)")

    console.print()
    if not Confirm.ask("Proceed?", default=True):
        raise SystemExit(0)

    # Create epic (suppress its own "Next:" footer by capturing return value)
    console.rule("Creating epic")
    epics_path = repo_root / "docs" / "focal" / "epics.md"
    if not epics_path.exists():
        console.print(
            "[red]docs/focal/epics.md not found. Run [bold]focal pm init[/bold] first.[/red]"
        )
        return

    epic_id = _next_epic_id(epics_path)
    assignee = config.get("assignee", "")
    board_number = config.get("board_number")
    board_owner = config.get("board_owner", "")

    epic_body = (
        f"## Vision\n\n{fm.get('title', breakdown['epic_title'])}\n\n"
        "## Stories\n\n<!-- Stories will be added here as sub-issues -->\n\n"
        "## Acceptance criteria\n\n<!-- What must be true for this epic to be done? -->"
    )

    try:
        epic_issue = gh.create_issue(
            repo=repo,
            title=f"Epic: {breakdown['epic_title']}",
            body=epic_body,
            labels=["epic"],
            assignee=assignee,
        )
    except RuntimeError as e:
        console.print(f"[red]Failed to create epic: {e}[/red]")
        return

    epic_number = epic_issue["number"]
    epic_url = epic_issue["url"]
    epic_db_id = epic_issue["id"]
    console.print(
        f"  [green]✔[/green] Epic #{epic_number} — Epic: {breakdown['epic_title']}"
    )

    # Add epic to board
    if board_number and board_owner:
        try:
            item_id = gh.add_item_get_id(board_number, board_owner, epic_url)
            estimate_field_id = config.get("estimate_field_id")
            if estimate_field_id and breakdown["epic_sp"] > 0:
                pid = gh.project_id(board_number, board_owner)
                gh.set_item_number_field(
                    pid, item_id, estimate_field_id, breakdown["epic_sp"]
                )
        except RuntimeError as e:
            console.print(f"  [yellow]⚠[/yellow]  Board update failed: {e}")

    state = pm_state.load(repo_root)
    state["repo"] = repo
    pm_state.upsert_epic(
        state,
        {
            "id": epic_id,
            "title": breakdown["epic_title"],
            "issue_number": epic_number,
            "issue_url": epic_url,
            "issue_db_id": epic_db_id,
            "sp": breakdown["epic_sp"],
            "status": "open",
            "stories": [],
        },
    )
    pm_state.save(repo_root, state)

    # Create stories
    console.rule("Creating stories")
    for story in breakdown["stories"]:
        story_body = (
            f"Part of epic #{epic_number}.\n\n"
            f"{story['title']}\n\n"
            f"**Estimated:** {story['sp']} SP"
        )
        try:
            story_issue = gh.create_issue(
                repo=repo,
                title=story["title"],
                body=story_body,
                labels=["story"],
                assignee=assignee,
            )
        except RuntimeError as e:
            console.print(
                f"  [red]Failed to create story '{story['title']}': {e}[/red]"
            )
            continue

        s_number = story_issue["number"]
        s_url = story_issue["url"]
        console.print(f"  [green]✔[/green] Story #{s_number} — {story['title']}")

        # Link as sub-issue
        try:
            gh.link_sub_issue(repo, epic_number, story_issue["id"])
        except RuntimeError as e:
            console.print(f"  [yellow]⚠[/yellow]  Sub-issue link failed: {e}")

        # Add to board
        if board_number and board_owner:
            try:
                item_id = gh.add_item_get_id(board_number, board_owner, s_url)
                estimate_field_id = config.get("estimate_field_id")
                if estimate_field_id and story["sp"] > 0:
                    pid = gh.project_id(board_number, board_owner)
                    gh.set_item_number_field(
                        pid, item_id, estimate_field_id, story["sp"]
                    )
            except RuntimeError as e:
                console.print(f"  [yellow]⚠[/yellow]  Board update failed: {e}")

        # Derive story ID from state
        from .story_cmd import _next_story_id_from_state

        story_id = _next_story_id_from_state(state, epic_id)

        # Update state
        state = pm_state.load(repo_root)
        pm_state.upsert_story(
            state,
            epic_id,
            {
                "id": story_id,
                "title": story["title"],
                "issue_number": s_number,
                "issue_url": s_url,
                "issue_db_id": story_issue["id"],
                "sp": story["sp"],
                "assignee": assignee,
                "status": "open",
                "project_status": "",
            },
        )
        pm_state.save(repo_root, state)

    # Re-render epics.md from final state
    final_state = pm_state.load(repo_root)
    epics_renderer.render(repo_root, final_state)
    console.print("  [green]✔[/green] docs/focal/epics.md updated")

    # Update design doc frontmatter
    console.rule("Updating design doc")
    rewrite_frontmatter(
        design_path,
        {
            "status": "Active",
            "epic": str(epic_number),
            "updated": str(date.today()),
        },
    )
    console.print(
        f"  [green]✔[/green] {design_path.name} — status: {doc_status} → Active, epic: #{epic_number}"
    )

    # Commit everything
    subprocess.run(
        ["git", "add", "docs/focal/epics.md", str(design_path)],
        cwd=repo_root,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            f"chore: create epic #{epic_number} + {len(breakdown['stories'])} stories from {doc_id}",
        ],
        cwd=repo_root,
        capture_output=True,
    )
    console.print("  [green]✔[/green] Committed")

    console.print(
        f"\n[bold green]Done![/bold green]  Epic #{epic_number} + {len(breakdown['stories'])} stories created."
    )
    console.print(f"  Epic:    {epic_url}")
    console.print(f"  Design:  {design_path.name} → Active")
