"""focal pm plan — generate/update docs/focal/iteration-planning.md."""

import subprocess
from datetime import date, timedelta
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from . import pm_state

console = Console()

SLIP_REASONS = ["SCOPE", "BLOCKED", "LEAVE", "TRAVEL", "CARRY", "REPRIORITY"]


# ── Date helpers ──────────────────────────────────────────────────────────────


def _parse_date(s: str) -> date:
    return date.fromisoformat(s.strip())


def _next_monday(d: date) -> date:
    days_ahead = 0 - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


def _iter_end(start: date, weeks: int) -> date:
    return start + timedelta(weeks=weeks) - timedelta(days=1)


def _format_date(d: date) -> str:
    return d.strftime("%b %-d, %Y")


# ── Capacity prompts ──────────────────────────────────────────────────────────


def _prompt_team(config: dict) -> list[dict]:
    """Prompt for team members and their SP capacity per iteration."""
    console.print("\n[bold]Team & capacity[/bold]")
    assignee = config.get("assignee", "")
    default_handles = assignee if assignee else ""
    raw = Prompt.ask("GitHub handles (comma-separated)", default=default_handles)
    handles = [h.strip().lstrip("@") for h in raw.split(",") if h.strip()]

    members = []
    for handle in handles:
        sp = Prompt.ask(f"  Capacity for @{handle} (SP/iter)", default="8")
        try:
            sp_int = int(sp)
        except ValueError:
            sp_int = 8
        members.append({"handle": handle, "sp_per_iter": sp_int})
    return members


def _prompt_pto(members: list[dict], iters: list[dict]) -> list[dict]:
    """Prompt for PTO/travel and reduce capacity for affected iterations."""
    if not Confirm.ask("\nAny PTO or travel to account for?", default=False):
        return iters

    console.print("\nEnter PTO dates (leave blank to finish):")
    while True:
        raw_handle = Prompt.ask("  GitHub handle (or blank to finish)", default="")
        if not raw_handle:
            break
        handle = raw_handle.lstrip("@")
        raw_start = Prompt.ask(f"  @{handle} away from (YYYY-MM-DD)")
        raw_end = Prompt.ask(f"  @{handle} away until (YYYY-MM-DD)")
        try:
            away_start = _parse_date(raw_start)
            away_end = _parse_date(raw_end)
        except ValueError:
            console.print("  [yellow]Invalid dates — skipping[/yellow]")
            continue

        # Find member's capacity contribution
        member = next((m for m in members if m["handle"] == handle), None)
        if not member:
            console.print(f"  [yellow]@{handle} not in team — skipping[/yellow]")
            continue

        full_sp = member["sp_per_iter"]
        for it in iters:
            iter_start = _parse_date(it["start"])
            iter_end_d = _parse_date(it["end"])
            # Overlap?
            if away_start <= iter_end_d and away_end >= iter_start:
                overlap_days = (
                    min(away_end, iter_end_d) - max(away_start, iter_start)
                ).days + 1
                iter_days = (iter_end_d - iter_start).days + 1
                reduction = round(full_sp * overlap_days / iter_days)
                it["capacity_sp"] = max(0, it["capacity_sp"] - reduction)
                it.setdefault("notes", []).append(
                    f"@{handle} away {_format_date(away_start)}–{_format_date(away_end)}"
                )
    return iters


# ── Iteration schedule builder ────────────────────────────────────────────────


def _build_iterations(
    start: date, weeks: int, num_iters: int, members: list[dict]
) -> list[dict]:
    base_capacity = sum(m["sp_per_iter"] for m in members)
    iters = []
    for i in range(num_iters):
        iter_start = start + timedelta(weeks=weeks * i)
        iter_end = _iter_end(iter_start, weeks)
        iters.append(
            {
                "number": i + 1,
                "label": f"I{i + 1}",
                "start": iter_start.isoformat(),
                "end": iter_end.isoformat(),
                "capacity_sp": base_capacity,
                "story_ids": [],
                "notes": [],
            }
        )
    return iters


def _assign_stories_to_iters(stories: list[dict], iters: list[dict]) -> list[dict]:
    """Greedily pack open stories into iterations by SP capacity."""
    open_stories = [s for s in stories if s.get("status") != "closed"]
    # Sort: stories with no SP last (unblocking known work first)
    open_stories.sort(
        key=lambda s: (s.get("sp", 0) == 0, s.get("epic_id", ""), s["id"])
    )

    remaining = list(open_stories)
    for it in iters:
        budget = it["capacity_sp"]
        assigned = []
        leftover = []
        for story in remaining:
            sp = story.get("sp", 0)
            if sp <= budget:
                assigned.append(story["id"])
                budget -= sp
            else:
                leftover.append(story)
        it["story_ids"] = assigned
        remaining = leftover
        if not remaining:
            break

    return iters


# ── Risk identification ───────────────────────────────────────────────────────


def _identify_risks(stories: list[dict]) -> list[dict]:
    risks = []
    no_sp = [s for s in stories if s.get("status") != "closed" and not s.get("sp")]
    if no_sp:
        risks.append(
            {
                "severity": "🟡 Medium",
                "risk": f"{len(no_sp)} stories have no SP estimate",
                "mitigation": "Estimate before planning: "
                + ", ".join(f"#{s['issue_number']}" for s in no_sp[:5]),
            }
        )
    unassigned = [
        s for s in stories if s.get("status") != "closed" and not s.get("assignee")
    ]
    if unassigned:
        risks.append(
            {
                "severity": "🟡 Medium",
                "risk": f"{len(unassigned)} stories have no assignee",
                "mitigation": "Assign before iteration starts",
            }
        )
    blocked = [
        s
        for s in stories
        if s.get("project_status", "").lower() in ("blocked", "✋ blocked")
    ]
    if blocked:
        risks.append(
            {
                "severity": "🔴 High",
                "risk": f"{len(blocked)} stories are blocked: "
                + ", ".join(f"#{s['issue_number']}" for s in blocked),
                "mitigation": "Resolve blockers before iteration starts",
            }
        )
    return risks


# ── Markdown renderer ─────────────────────────────────────────────────────────


def _render(
    repo: str,
    members: list[dict],
    iters: list[dict],
    risks: list[dict],
    all_stories: list[dict],
    weeks: int,
) -> str:
    story_map = {s["id"]: s for s in all_stories}
    total_sp = sum(s.get("sp", 0) for s in all_stories if s.get("status") != "closed")
    total_cap = sum(it["capacity_sp"] for it in iters)
    last_iter = iters[-1] if iters else None
    projected_end = _format_date(_parse_date(last_iter["end"])) if last_iter else "TBD"

    lines = [
        "# Iteration Planning",
        "",
        f"Repo: `{repo}`",
        f"Total scope: **{total_sp} SP** open across "
        f"{sum(1 for s in all_stories if s.get('status') != 'closed')} stories",
        "",
        "---",
        "",
        "## Team",
        "",
        "| Handle | SP/iter |",
        "|--------|---------|",
    ]
    for m in members:
        lines.append(f"| @{m['handle']} | {m['sp_per_iter']} |")

    lines += [
        "",
        "---",
        "",
        "## Iteration Setup",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Length | {weeks} weeks |",
        f"| Start date | {iters[0]['start'] if iters else 'TBD'} |",
        f"| Team velocity | ~{sum(m['sp_per_iter'] for m in members)} SP/iteration |",
        f"| Total capacity ({len(iters)} iters) | {total_cap} SP |",
        f"| Projected end | {projected_end} (I{len(iters)}) |",
    ]

    if total_sp > total_cap:
        gap = total_sp - total_cap
        lines.append("")
        lines.append(
            f"> ⚠️ Scope {total_sp} SP vs {total_cap} SP capacity — "
            f"{gap} SP gap. Scope de-prioritisation may be needed."
        )

    if risks:
        lines += [
            "",
            "---",
            "",
            "## Risks",
            "",
            "| Severity | Risk | Mitigation |",
            "|----------|------|------------|",
        ]
        for r in risks:
            lines.append(f"| {r['severity']} | {r['risk']} | {r['mitigation']} |")

    lines += ["", "---", "", "## Iteration Schedule", ""]

    for it in iters:
        start_d = _parse_date(it["start"])
        end_d = _parse_date(it["end"])
        header = (
            f"### {it['label']} — {_format_date(start_d)} – {_format_date(end_d)} "
            f"· {it['capacity_sp']} SP"
        )
        lines.append(header)
        lines.append("")
        if it["notes"]:
            for note in it["notes"]:
                lines.append(f"> ⚠️ {note}")
            lines.append("")
        if it["story_ids"]:
            lines.append("| Story | Title | Epic | SP | Assignee |")
            lines.append("|-------|-------|------|----|----------|")
            for sid in it["story_ids"]:
                s = story_map.get(sid, {})
                lines.append(
                    f"| [{sid}](https://github.com/{repo}/issues/{s.get('issue_number', '')}) "
                    f"| {s.get('title', '')} "
                    f"| {s.get('epic_id', '')} "
                    f"| {s.get('sp', '—')} "
                    f"| @{s.get('assignee', '—')} |"
                )
        else:
            lines.append("_No stories assigned yet._")
        lines.append("")

    # Unscheduled stories
    scheduled_ids = {sid for it in iters for sid in it["story_ids"]}
    unscheduled = [
        s
        for s in all_stories
        if s["id"] not in scheduled_ids and s.get("status") != "closed"
    ]
    if unscheduled:
        lines += [
            "---",
            "",
            "## Unscheduled (beyond current plan)",
            "",
            "| Story | Title | Epic | SP |",
            "|-------|-------|------|----|",
        ]
        for s in unscheduled:
            lines.append(
                f"| [{s['id']}](https://github.com/{repo}/issues/{s.get('issue_number', '')}) "
                f"| {s.get('title', '')} | {s.get('epic_id', '')} | {s.get('sp', '—')} |"
            )

    return "\n".join(lines) + "\n"


def _git_commit(repo_root: Path, message: str) -> None:
    subprocess.run(
        ["git", "add", "docs/focal/iteration-planning.md"],
        cwd=repo_root,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        capture_output=True,
    )


# ── Main entry ────────────────────────────────────────────────────────────────


def run(repo: str, repo_root: Path, config: dict, refresh: bool = False) -> None:
    """Generate or update docs/focal/iteration-planning.md."""
    console.print(f"\n[bold cyan]  ◎  Focal — plan ({repo})[/bold cyan]\n")

    state = pm_state.load(repo_root)
    if not state["epics"]:
        console.print(
            "[red]No epics in local state. "
            "Run [bold]focal cache refresh[/bold] or create epics first.[/red]"
        )
        return

    if refresh:
        console.print("Refreshing state from GitHub...")
        state = pm_state.refresh_from_github(repo_root, repo, config)
        console.print("  [green]✔[/green] State refreshed")

    stories = pm_state.all_stories(state)
    open_stories = [s for s in stories if s.get("status") != "closed"]
    closed_count = len(stories) - len(open_stories)
    total_sp = sum(s.get("sp", 0) for s in open_stories)

    console.print(
        f"Found [bold]{len(open_stories)}[/bold] open stories "
        f"({closed_count} closed) · [bold]{total_sp} SP[/bold] total\n"
    )

    # Iteration parameters
    console.print("[bold]Iteration parameters[/bold]")
    weeks_raw = Prompt.ask("Iteration length (weeks)", default="2")
    weeks = int(weeks_raw) if weeks_raw.isdigit() else 2

    today = date.today()
    default_start = _next_monday(today).isoformat()
    start_raw = Prompt.ask("Start date (YYYY-MM-DD)", default=default_start)
    try:
        start = _parse_date(start_raw)
    except ValueError:
        start = _next_monday(today)

    # Estimate number of iterations needed
    members = _prompt_team(config)
    base_cap = sum(m["sp_per_iter"] for m in members)
    if base_cap > 0:
        num_iters = max(1, -(-total_sp // base_cap) + 1)  # ceiling + 1 buffer
    else:
        num_iters = 8
    num_iters = min(num_iters, 24)  # cap at 24

    iters = _build_iterations(start, weeks, num_iters, members)
    iters = _prompt_pto(members, iters)
    iters = _assign_stories_to_iters(open_stories, iters)

    # Trim trailing empty iterations
    while iters and not iters[-1]["story_ids"]:
        iters.pop()
    if not iters:
        iters = _build_iterations(start, weeks, 1, members)

    risks = _identify_risks(open_stories)

    # Render and write
    plan_path = repo_root / "docs" / "focal" / "iteration-planning.md"
    plan_path.write_text(_render(repo, members, iters, risks, stories, weeks))
    console.print("\n  [green]✔[/green] docs/focal/iteration-planning.md written")

    # Persist iteration schedule to state
    state["iterations"] = [{k: v for k, v in it.items()} for it in iters]
    pm_state.save(repo_root, state)
    console.print("  [green]✔[/green] Local state updated")

    _git_commit(repo_root, "chore: update iteration-planning.md")
    console.print("  [green]✔[/green] Committed")

    console.print(
        f"\n[bold green]Plan generated — {len(iters)} iteration(s)[/bold green]"
    )
    if risks:
        console.print(
            f"  [yellow]⚠[/yellow]  {len(risks)} risk(s) flagged — review the plan"
        )
