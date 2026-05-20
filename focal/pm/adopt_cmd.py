"""focal pm adopt — onboard an existing GitHub repo into Focal PM management."""

import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import IntPrompt
from rich.table import Table

from . import pm_state
from .hierarchy_resolver import resolve as resolve_hierarchy
from .sp_extractor import extract_sp

console = Console()


# ── GitHub helpers (thin wrappers used only by adopt) ─────────────────────────


def _gh_edit_issue(repo: str, number: int, **kwargs: str) -> None:
    args = ["gh", "issue", "edit", str(number), "--repo", repo]
    for flag, value in kwargs.items():
        args += [f"--{flag}", value]
    subprocess.run(args, check=True, capture_output=True)


# ── Discovery ─────────────────────────────────────────────────────────────────


def _prompt_sp(issue: dict) -> int:
    console.print(
        f"  [yellow]?[/yellow]  #{issue['number']} — {issue['title']}"
    )
    return IntPrompt.ask("    Estimate (story points)", default=0)


def _discover(
    repo: str,
    epic_labels: list[str],
    story_labels: list[str],
    sp_field: str,
    default_sp: Optional[int],
    prompt_missing: bool,
) -> tuple[list[dict], list[dict], list[str]]:
    """Fetch issues and enrich with SP + hierarchy.

    Returns (epics, stories, warnings).
    Each epic/story dict has: number, title, body, state, url, labels,
    assignees, sp (int|None), sub_issues (list[int] for epics).
    """
    from .. import gh

    console.print("Scanning issues…")

    epics_raw = gh.issues_by_label(repo, epic_labels, state="open")
    stories_raw = gh.issues_by_label(repo, story_labels, state="open")

    # Remove any issue that appears in both (edge case: labelled both)
    epic_numbers = {e["number"] for e in epics_raw}
    stories_raw = [s for s in stories_raw if s["number"] not in epic_numbers]

    total = len(epics_raw) + len(stories_raw)
    label_desc = " or ".join(f"'{lb}'" for lb in epic_labels + story_labels)
    console.print(f"  Found {total} issues with label {label_desc}\n")

    # Fetch sub-issues for each epic
    sub_issue_map: dict[int, list[int]] = {}
    for epic in epics_raw:
        children = gh.issue_sub_issues(repo, epic["number"])
        sub_issue_map[epic["number"]] = [c["number"] for c in children]

    # Resolve hierarchy
    parent_map = resolve_hierarchy(epics_raw, stories_raw, sub_issue_map)

    warnings: list[str] = []

    # Enrich epics with SP
    epics: list[dict] = []
    missing_sp_epics = []
    for e in epics_raw:
        pf = gh.project_field_value(repo, e["number"], sp_field)
        sp = extract_sp(e, pf) or default_sp
        if sp is None:
            missing_sp_epics.append(e)
        epics.append({**e, "sp": sp, "sub_issues": sub_issue_map.get(e["number"], [])})

    if missing_sp_epics:
        if prompt_missing:
            console.print("\n[bold yellow]Missing SP estimates — epics:[/bold yellow]")
            for e in missing_sp_epics:
                sp = _prompt_sp(e)
                next(ep for ep in epics if ep["number"] == e["number"])["sp"] = sp
        else:
            for e in missing_sp_epics:
                warnings.append(
                    f"#{e['number']} — no SP estimate found (use --default-sp or --prompt-missing)"
                )

    # Enrich stories with SP + parent
    stories: list[dict] = []
    missing_sp_stories = []
    for s in stories_raw:
        pf = gh.project_field_value(repo, s["number"], sp_field)
        sp = extract_sp(s, pf) or default_sp
        parent = parent_map.get(s["number"])
        if sp is None:
            missing_sp_stories.append(s)
        if parent is None:
            warnings.append(
                f"#{s['number']} '{s['title']}' — no parent epic found (will be orphaned)"
            )
        stories.append({**s, "sp": sp, "parent_epic_number": parent})

    if missing_sp_stories:
        if prompt_missing:
            console.print("\n[bold yellow]Missing SP estimates — stories:[/bold yellow]")
            for s in missing_sp_stories:
                sp = _prompt_sp(s)
                next(st for st in stories if st["number"] == s["number"])["sp"] = sp
        else:
            for s in missing_sp_stories:
                warnings.append(
                    f"#{s['number']} '{s['title']}' — no SP estimate found (use --default-sp or --prompt-missing)"
                )

    return epics, stories, warnings


# ── ID assignment ─────────────────────────────────────────────────────────────


def _assign_ids(
    epics: list[dict], stories: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Assign stable E1/E2 IDs to epics and 1.1/1.2 IDs to stories."""
    sorted_epics = sorted(epics, key=lambda e: e["number"])
    epic_num_to_idx = {e["number"]: i + 1 for i, e in enumerate(sorted_epics)}

    for i, epic in enumerate(sorted_epics):
        epic["focal_id"] = f"E{i + 1}"

    story_counter: dict[int, int] = {}  # epic_idx → next story seq
    for s in sorted(stories, key=lambda s: s["number"]):
        parent = s["parent_epic_number"]
        if parent and parent in epic_num_to_idx:
            epic_idx = epic_num_to_idx[parent]
        else:
            epic_idx = 0  # orphaned → epic index 0
        story_counter[epic_idx] = story_counter.get(epic_idx, 0) + 1
        prefix = str(epic_idx) if epic_idx else "0"
        s["focal_id"] = f"{prefix}.{story_counter[epic_idx]}"

    return sorted_epics, stories


# ── Report ────────────────────────────────────────────────────────────────────


def _render_report(
    repo: str,
    epics: list[dict],
    stories: list[dict],
    warnings: list[str],
    apply: bool,
) -> None:
    console.print(f"\n[bold cyan]  ◎  Focal — adopt {repo}[/bold cyan]\n")

    # Epics table
    epic_table = Table(show_header=False, box=None, pad_edge=False)
    epic_table.add_column("ID", style="bold cyan", width=5)
    epic_table.add_column("Ref", width=6)
    epic_table.add_column("Title")
    epic_table.add_column("SP", width=6)
    epic_table.add_column("Stories", width=10)

    story_count_by_epic: dict[int, int] = {}
    for s in stories:
        p = s.get("parent_epic_number")
        if p:
            story_count_by_epic[p] = story_count_by_epic.get(p, 0) + 1

    for e in epics:
        sp_str = (
            str(e["sp"]) + " SP" if e["sp"] is not None else "[yellow]— SP ⚠[/yellow]"
        )
        n_stories = story_count_by_epic.get(e["number"], 0)
        epic_table.add_row(
            e["focal_id"], f"#{e['number']}", e["title"], sp_str, f"{n_stories} stories"
        )

    console.print(f"[bold]Epics discovered ({len(epics)})[/bold]")
    console.print(epic_table)

    # Stories table
    console.print(f"\n[bold]Stories discovered ({len(stories)})[/bold]")
    story_table = Table(show_header=False, box=None, pad_edge=False)
    story_table.add_column("ID", style="bold", width=6)
    story_table.add_column("Ref", width=6)
    story_table.add_column("Title")
    story_table.add_column("SP", width=6)
    story_table.add_column("Link", width=16)

    epic_number_to_focal_id = {e["number"]: e["focal_id"] for e in epics}
    for s in stories:
        sp_str = (
            str(s["sp"]) + " SP" if s["sp"] is not None else "[yellow]— SP ⚠[/yellow]"
        )
        parent = s.get("parent_epic_number")
        if parent:
            link = f"[green]✔ linked to {epic_number_to_focal_id.get(parent, f'#{parent}')}[/green]"
        else:
            link = "[yellow]⚠ orphaned[/yellow]"
        story_table.add_row(s["focal_id"], f"#{s['number']}", s["title"], sp_str, link)

    console.print(story_table)

    # Warnings
    if warnings:
        console.print(f"\n[bold yellow]Warnings ({len(warnings)})[/bold yellow]")
        for w in warnings:
            console.print(f"  [yellow]⚠[/yellow]  {w}")

    # Summary
    orphaned = sum(1 for s in stories if s.get("parent_epic_number") is None)
    console.print("\n[bold]Summary[/bold]")
    console.print(
        f"  {len(epics)} epics  ·  {len(stories)} stories  ·  "
        f"0 iterations (run [bold]focal pm plan[/bold] next)"
    )
    if orphaned:
        console.print(
            f"  [yellow]{orphaned} orphaned stories[/yellow] — add to an epic or run with --normalise"
        )
    if not apply:
        console.print(
            "\n  [dim]Dry run — no files written. Pass --apply to bootstrap state cache.[/dim]"
        )


# ── State bootstrap ───────────────────────────────────────────────────────────


def _bootstrap_state(
    repo: str,
    repo_root: Path,
    epics: list[dict],
    stories: list[dict],
) -> None:
    """Merge discovered issues into focal-state.json (create if absent)."""
    state = pm_state.load(repo_root)
    state["repo"] = repo

    # Build lookup of existing epics/stories by issue_number to preserve data
    existing_epics = {e["issue_number"]: e for e in state.get("epics", [])}

    epic_number_to_focal_id = {e["number"]: e["focal_id"] for e in epics}

    new_stories_by_epic: dict[str, list[dict]] = {e["focal_id"]: [] for e in epics}
    orphan_stories: list[dict] = []

    for s in stories:
        parent_num = s.get("parent_epic_number")
        parent_focal_id = (
            epic_number_to_focal_id.get(parent_num) if parent_num else None
        )
        story_entry = {
            "id": s["focal_id"],
            "title": s["title"],
            "issue_number": s["number"],
            "issue_url": s["url"],
            "sp": s["sp"],
            "assignee": s["assignees"][0] if s["assignees"] else "",
            "status": s["state"],
            "project_status": "",
        }
        if parent_focal_id:
            new_stories_by_epic[parent_focal_id].append(story_entry)
        else:
            orphan_stories.append(story_entry)

    new_epics = []
    for e in epics:
        existing = existing_epics.get(e["number"], {})
        epic_entry = {
            "id": e["focal_id"],
            "title": e["title"],
            "issue_number": e["number"],
            "issue_url": e["url"],
            "sp": e["sp"] if e["sp"] is not None else existing.get("sp"),
            "status": e["state"],
            "stories": new_stories_by_epic.get(
                e["focal_id"], existing.get("stories", [])
            ),
        }
        new_epics.append(epic_entry)

    # Preserve existing epics not found in this scan, merge new ones
    merged_by_number = {e["issue_number"]: e for e in state.get("epics", [])}
    for epic in new_epics:
        merged_by_number[epic["issue_number"]] = epic
    state["epics"] = list(merged_by_number.values())

    # Orphaned stories — attach to a synthetic "orphaned" epic or surface as-is
    if orphan_stories:
        orphan_epic_id = "E0"
        orphan_epic = next(
            (e for e in state["epics"] if e.get("id") == orphan_epic_id), None
        )
        if orphan_epic:
            existing_orphan_nums = {s["issue_number"] for s in orphan_epic["stories"]}
            for s in orphan_stories:
                if s["issue_number"] not in existing_orphan_nums:
                    orphan_epic["stories"].append(s)
        else:
            state["epics"].insert(
                0,
                {
                    "id": orphan_epic_id,
                    "title": "(Orphaned stories — no parent epic found)",
                    "issue_number": 0,
                    "issue_url": "",
                    "sp": None,
                    "status": "open",
                    "stories": orphan_stories,
                },
            )

    state.setdefault("iterations", [])
    pm_state.save(repo_root, state)
    path = pm_state.state_path(repo_root)
    console.print(f"\n  [green]✔[/green] State bootstrapped → {path}")


# ── Normalise ─────────────────────────────────────────────────────────────────


def _normalise(
    repo: str,
    epics: list[dict],
    stories: list[dict],
    epic_labels: list[str],
    story_labels: list[str],
) -> None:
    """Re-label issues, move SP from title to body table, create missing sub-issue links."""
    from .. import gh

    console.print("\n[bold]Normalising issues…[/bold]")
    canonical_epic_label = "epic"
    canonical_story_label = "story"

    def _needs_relabel(issue: dict, canonical: str, current_labels: list[str]) -> bool:
        return canonical not in issue["labels"]

    def _sp_in_title(title: str) -> bool:
        import re

        return bool(re.search(r"\[\d+\]|\(\d+\s*SP\)|\d+\s*SP\b", title, re.IGNORECASE))

    def _strip_sp_from_title(title: str) -> str:
        import re

        title = re.sub(r"\s*\[\d+\]\s*", " ", title)
        title = re.sub(r"\s*\(\d+\s*SP\)\s*", " ", title, flags=re.IGNORECASE)
        title = re.sub(r"\s*#?\d+\s*SP\b\s*", " ", title, flags=re.IGNORECASE)
        return title.strip()

    def _sp_in_body(body: str) -> bool:
        import re

        return bool(
            re.search(
                r"^\|\s*(?:SP|Story\s+Points)\s*\|\s*\d+\s*\|",
                body,
                re.IGNORECASE | re.MULTILINE,
            )
        )

    for epic in epics:
        # Re-label
        if _needs_relabel(epic, canonical_epic_label, epic["labels"]):
            non_focal = [
                lb
                for lb in epic["labels"]
                if lb in epic_labels and lb != canonical_epic_label
            ]
            _gh_edit_issue(repo, epic["number"], **{"add-label": canonical_epic_label})
            for lb in non_focal:
                _gh_edit_issue(repo, epic["number"], **{"remove-label": lb})
            console.print(f"  [green]✔[/green] #{epic['number']} re-labelled → epic")

    for story in stories:
        # Re-label
        if _needs_relabel(story, canonical_story_label, story["labels"]):
            non_focal = [
                lb
                for lb in story["labels"]
                if lb in story_labels and lb != canonical_story_label
            ]
            _gh_edit_issue(
                repo, story["number"], **{"add-label": canonical_story_label}
            )
            for lb in non_focal:
                _gh_edit_issue(repo, story["number"], **{"remove-label": lb})
            console.print(f"  [green]✔[/green] #{story['number']} re-labelled → story")

        # Move SP from title to body
        if _sp_in_title(story["title"]) and story["sp"] is not None:
            new_title = _strip_sp_from_title(story["title"])
            _gh_edit_issue(repo, story["number"], title=new_title)
            console.print(
                f"  [green]✔[/green] #{story['number']} SP removed from title"
            )

        # Add SP to body table if missing
        if story["sp"] is not None and not _sp_in_body(story.get("body", "")):
            parent = story.get("parent_epic_number")
            parent_line = f"Part of #{parent}\n\n" if parent else ""
            sp_table = f"| SP | {story['sp']} |\n|---|---|\n"
            existing_body = story.get("body", "").strip()
            if existing_body:
                new_body = f"{existing_body}\n\n{sp_table}"
            else:
                new_body = f"{parent_line}{sp_table}"
            _gh_edit_issue(repo, story["number"], body=new_body)
            console.print(f"  [green]✔[/green] #{story['number']} SP added to body")

        # Create sub-issue link if inferred (not from API)
        parent_num = story.get("parent_epic_number")
        if parent_num and story["number"] not in _get_existing_sub_issues(
            repo, parent_num
        ):
            try:
                gh.link_sub_issue(repo, parent_num, _database_id(repo, story["number"]))
                console.print(
                    f"  [green]✔[/green] #{story['number']} linked as sub-issue of #{parent_num}"
                )
            except Exception as exc:
                console.print(
                    f"  [yellow]⚠[/yellow] Could not link #{story['number']}: {exc}"
                )


def _get_existing_sub_issues(repo: str, parent_number: int) -> set[int]:
    from .. import gh

    return {c["number"] for c in gh.issue_sub_issues(repo, parent_number)}


def _database_id(repo: str, issue_number: int) -> int:
    from .. import gh

    owner, name = repo.split("/", 1)
    data = gh._graphql(
        f'{{ repository(owner: "{owner}", name: "{name}") {{ issue(number: {issue_number}) {{ databaseId }} }} }}'
    )
    return data["data"]["repository"]["issue"]["databaseId"]


# ── Main entry point ──────────────────────────────────────────────────────────


def run(
    repo: str,
    repo_root: Path,
    epic_labels: list[str],
    story_labels: list[str],
    sp_field: str,
    default_sp: Optional[int],
    apply: bool,
    normalise: bool,
    prompt_missing: bool = False,
) -> None:
    epics, stories, warnings = _discover(
        repo, epic_labels, story_labels, sp_field, default_sp, prompt_missing
    )
    epics, stories = _assign_ids(epics, stories)
    _render_report(repo, epics, stories, warnings, apply)

    if apply:
        repo_root.mkdir(parents=True, exist_ok=True)
        _bootstrap_state(repo, repo_root, epics, stories)

        if normalise:
            _normalise(repo, epics, stories, epic_labels, story_labels)
