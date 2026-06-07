"""focal pm adopt-plan — bootstrap GitHub issues from docs/focal/plan.md."""

from __future__ import annotations

import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .. import gh
from . import epics_renderer, pm_state
from .plan_doc_parser import ParsedEpic, ParsedStory, parse

console = Console()

_DEFAULT_PLAN = Path("docs/focal/plan.md")


def _issue_body_epic(title: str) -> str:
    return (
        f"## Vision\n\n{title}\n\n"
        "## Stories\n\n<!-- Stories will be added here as sub-issues -->\n\n"
        "## Acceptance criteria\n\n<!-- What must be true for this epic to be done? -->"
    )


def _issue_body_story(epic_number: int, sp: int) -> str:
    return f"Part of epic #{epic_number}.\n\n| SP | {sp} |\n|---|---|"


def _print_dry_run(
    repo: str,
    epics_to_create: list[ParsedEpic],
    stories_to_create: list[tuple[ParsedEpic, ParsedStory]],
) -> None:
    if not epics_to_create and not stories_to_create:
        console.print(
            "[green]Nothing to create — all epics and stories already tracked.[/green]"
        )
        return

    console.print(f"\n[bold]Dry run — would create for [cyan]{repo}[/cyan]:[/bold]\n")

    if epics_to_create:
        t = Table("ID", "Title", "SP", title="Epics", show_header=True)
        for e in epics_to_create:
            t.add_row(e.local_id, e.title, str(e.sp) if e.sp is not None else "ongoing")
        console.print(t)

    if stories_to_create:
        t = Table("ID", "Epic", "Title", "SP", title="Stories", show_header=True)
        for epic, story in stories_to_create:
            t.add_row(story.local_id, epic.local_id, story.title, str(story.sp))
        console.print(t)

    console.print(
        f"\nRun with [bold]--apply[/bold] to create {len(epics_to_create)} epic(s) "
        f"and {len(stories_to_create)} story/stories."
    )


def run(
    repo: str,
    repo_root: Path,
    config: dict,
    plan_path: Path | None = None,
    apply: bool = False,
) -> None:
    """Bootstrap GitHub issues from plan.md."""
    console.print(f"\n[bold cyan]  ◎  Focal — adopt-plan ({repo})[/bold cyan]\n")

    path = plan_path or (repo_root / _DEFAULT_PLAN)
    if not path.exists():
        console.print(
            f"[red]Plan doc not found: {path}\n"
            "Run [bold]focal pm init[/bold] first, then edit [bold]docs/focal/plan.md[/bold].[/red]"
        )
        return

    doc = parse(path)

    # Resolve repo from plan doc if not provided via CLI
    if doc.repo and doc.repo != repo:
        console.print(
            f"[yellow]⚠[/yellow]  Plan doc references [bold]{doc.repo}[/bold] "
            f"but you passed [bold]{repo}[/bold]. Using [bold]{repo}[/bold]."
        )

    state = pm_state.load(repo_root)
    state["repo"] = repo
    tracked_epic_ids = {e["id"] for e in state.get("epics", [])}

    epics_to_create: list[ParsedEpic] = []
    stories_to_create: list[tuple[ParsedEpic, ParsedStory]] = []

    for epic in doc.epics:
        if epic.local_id not in tracked_epic_ids:
            epics_to_create.append(epic)
        else:
            existing_epic = pm_state.get_epic(state, epic.local_id)
            tracked_story_ids = (
                {s["id"] for s in existing_epic.get("stories", [])}
                if existing_epic
                else set()
            )
            for story in epic.stories:
                if story.local_id not in tracked_story_ids:
                    stories_to_create.append((epic, story))

    if not apply:
        _print_dry_run(repo, epics_to_create, stories_to_create)
        return

    # ── Apply ─────────────────────────────────────────────────────────────────
    assignee = config.get("assignee", "")
    board_number = config.get("board_number")
    board_owner = config.get("board_owner", "")

    # Track newly created epic numbers so stories can reference them
    epic_issue_map: dict[str, int] = {
        e["id"]: e["issue_number"]
        for e in state.get("epics", [])
        if e.get("issue_number")
    }

    for epic in epics_to_create:
        console.print(f"Creating epic [bold]{epic.local_id}[/bold] — {epic.title}...")
        try:
            issue = gh.create_issue(
                repo=repo,
                title=f"Epic: {epic.title}",
                body=_issue_body_epic(epic.title),
                labels=["epic"],
                assignee=assignee,
            )
        except RuntimeError as e:
            console.print(f"  [red]Failed: {e}[/red]")
            continue

        epic_issue_map[epic.local_id] = issue["number"]
        pm_state.upsert_epic(
            state,
            {
                "id": epic.local_id,
                "title": epic.title,
                "issue_number": issue["number"],
                "issue_url": issue["url"],
                "issue_db_id": issue["id"],
                "sp": epic.sp or 0,
                "status": "open",
                "stories": [],
            },
        )
        pm_state.save(repo_root, state)
        console.print(f"  [green]✔[/green] #{issue['number']} — {epic.title}")

        if board_number and board_owner:
            try:
                gh.add_item_get_id(board_number, board_owner, issue["url"])
            except RuntimeError as e:
                console.print(f"  [yellow]⚠[/yellow]  Board add failed: {e}")

    # Create all pending stories (including those under newly created epics)
    for epic, story in stories_to_create:
        epic_number = epic_issue_map.get(epic.local_id)
        if not epic_number:
            console.print(
                f"  [yellow]⚠[/yellow]  Skipping {story.local_id} — "
                f"parent epic {epic.local_id} has no issue number"
            )
            continue

        console.print(
            f"Creating story [bold]{story.local_id}[/bold] — {story.title}..."
        )
        try:
            issue = gh.create_issue(
                repo=repo,
                title=story.title,
                body=_issue_body_story(epic_number, story.sp),
                labels=["story"],
                assignee=assignee,
            )
        except RuntimeError as e:
            console.print(f"  [red]Failed: {e}[/red]")
            continue

        console.print(f"  [green]✔[/green] #{issue['number']} — {story.title}")

        # Link as sub-issue
        try:
            existing_epic_state = pm_state.get_epic(state, epic.local_id)
            if existing_epic_state:
                gh.link_sub_issue(repo, epic_number, issue["id"])
        except RuntimeError as e:
            console.print(f"  [yellow]⚠[/yellow]  Sub-issue link failed: {e}")

        state = pm_state.load(repo_root)
        pm_state.upsert_story(
            state,
            epic.local_id,
            {
                "id": story.local_id,
                "title": story.title,
                "issue_number": issue["number"],
                "issue_url": issue["url"],
                "issue_db_id": issue["id"],
                "sp": story.sp,
                "assignee": assignee,
                "status": "open",
                "project_status": "",
            },
        )
        pm_state.save(repo_root, state)

        if board_number and board_owner:
            try:
                item_id = gh.add_item_get_id(board_number, board_owner, issue["url"])
                estimate_field_id = config.get("estimate_field_id")
                if estimate_field_id and story.sp > 0:
                    pid = gh.project_id(board_number, board_owner)
                    gh.set_item_number_field(pid, item_id, estimate_field_id, story.sp)
            except RuntimeError as e:
                console.print(f"  [yellow]⚠[/yellow]  Board update failed: {e}")

    # Re-render epics.md from final state
    final_state = pm_state.load(repo_root)
    epics_renderer.render(repo_root, final_state)
    console.print("  [green]✔[/green] docs/focal/epics.md updated")

    subprocess.run(
        ["git", "add", "docs/focal/epics.md"],
        cwd=repo_root,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            f"chore: adopt-plan — {len(epics_to_create)} epic(s), {len(stories_to_create)} story/stories",
        ],
        cwd=repo_root,
        capture_output=True,
    )
    console.print("  [green]✔[/green] Committed")

    console.print(
        f"\n[bold green]Done![/bold green]  Adopted {len(epics_to_create)} epic(s) and {len(stories_to_create)} story/stories."
    )
    console.print("Run [bold]focal pm status[/bold] to see current state.")
