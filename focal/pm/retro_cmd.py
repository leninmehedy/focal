"""focal pm retro — log a completed iteration and update docs/focal/retro-log.md."""

import re
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from .. import gh
from . import pm_state

console = Console()

SLIP_REASONS = ["SCOPE", "BLOCKED", "LEAVE", "TRAVEL", "CARRY", "REPRIORITY"]

SLIP_DESCRIPTIONS = {
    "SCOPE": "scope added mid-iteration",
    "BLOCKED": "external blocker",
    "LEAVE": "unplanned leave",
    "TRAVEL": "travel / conference",
    "CARRY": "underestimated, carries forward",
    "REPRIORITY": "deprioritised by stakeholder",
}


# ── Iteration selection ───────────────────────────────────────────────────────


def _select_iteration(state: dict) -> dict | None:
    iters = state.get("iterations", [])
    if not iters:
        return None
    console.print("\nSelect iteration to close:\n")
    for i, it in enumerate(iters, 1):
        console.print(
            f"  [bold]{i}[/bold]  {it['label']} — {it['start']} → {it['end']}  ({it['capacity_sp']} SP)"
        )
    raw = Prompt.ask("\nChoice", default="1")
    try:
        return iters[int(raw) - 1]
    except (ValueError, IndexError):
        return None


# ── GitHub status check ───────────────────────────────────────────────────────


def _check_story_statuses(
    repo: str, iteration: dict, story_map: dict
) -> tuple[list[dict], list[dict]]:
    """Return (delivered, carry_over) based on current GitHub issue state."""
    delivered, carry_over = [], []
    for sid in iteration.get("story_ids", []):
        story = story_map.get(sid)
        if not story:
            continue
        try:
            issue = gh.issue_state(repo, story["issue_number"])
            status = issue["state"]
        except RuntimeError:
            status = story.get("status", "open")
        if status == "closed":
            delivered.append(story)
        else:
            carry_over.append(story)
    return delivered, carry_over


# ── Slip reason prompts ───────────────────────────────────────────────────────


def _prompt_slip_reasons(carry_over: list[dict]) -> list[dict]:
    """Prompt for a slip reason code per carry-over story."""
    if not carry_over:
        return []

    console.print("\n[bold]Slip reasons[/bold] (for carry-over stories)\n")
    console.print("Codes: " + " · ".join(f"[bold]{c}[/bold]" for c in SLIP_REASONS))
    console.print("")

    slips = []
    for story in carry_over:
        default_code = "CARRY"
        raw = Prompt.ask(
            f"  #{story['issue_number']} {story['title']} [{story.get('sp', '?')} SP]",
            default=default_code,
        ).upper()
        code = raw if raw in SLIP_REASONS else "CARRY"
        note = Prompt.ask("    Optional note (blank to skip)", default="")
        slips.append({"story": story, "code": code, "note": note.strip()})
    return slips


# ── Qualitative prompts ───────────────────────────────────────────────────────


def _prompt_goal_met(goal: str) -> tuple[bool | None, str]:
    """Ask whether the iteration goal was met. Returns (met, reason)."""
    if not goal:
        return None, ""
    console.print(f"\n[bold]Iteration goal:[/bold] {goal}")
    met = Confirm.ask("  Goal met?", default=True)
    reason = ""
    if not met:
        reason = Prompt.ask("  Briefly, why not?", default="")
    return met, reason.strip()


def _prompt_bullets(prompt_label: str) -> list[str]:
    """Prompt for a bulleted list, one item per line, blank to finish."""
    console.print(f"\n[bold]{prompt_label}[/bold] (one per line, blank to finish)")
    items = []
    while True:
        item = Prompt.ask("  •", default="")
        if not item.strip():
            break
        items.append(item.strip())
    return items


def _prompt_action_items() -> list[dict]:
    """Prompt for action items with owner and due date."""
    console.print("\n[bold]Action items[/bold] (blank handle to finish)")
    items = []
    while True:
        handle = Prompt.ask("  Owner handle (or blank to finish)", default="").lstrip(
            "@"
        )
        if not handle:
            break
        action = Prompt.ask(f"  @{handle}: action")
        due = Prompt.ask("  Due date (YYYY-MM-DD, blank to skip)", default="")
        items.append({"handle": handle, "action": action.strip(), "due": due.strip()})
    return items


# ── Velocity calculation ──────────────────────────────────────────────────────


def _velocity(delivered: list[dict], carry_over: list[dict], capacity_sp: int) -> dict:
    planned_sp = sum(s.get("sp", 0) for s in delivered + carry_over)
    delivered_sp = sum(s.get("sp", 0) for s in delivered)
    carry_sp = sum(s.get("sp", 0) for s in carry_over)
    return {
        "planned_sp": planned_sp,
        "delivered_sp": delivered_sp,
        "carry_sp": carry_sp,
        "capacity_sp": capacity_sp,
    }


# ── Markdown helpers ──────────────────────────────────────────────────────────


def _format_date(s: str) -> str:
    from datetime import date

    d = date.fromisoformat(s)
    return d.strftime("%b %-d, %Y")


def _render_iteration_block(
    repo: str,
    iteration: dict,
    delivered: list[dict],
    carry_over: list[dict],
    slips: list[dict],
    vel: dict,
    goal: str,
    goal_met: bool | None,
    goal_reason: str,
    went_well: list[str],
    to_improve: list[str],
    action_items: list[dict],
    notes: str,
) -> str:
    label = iteration["label"]
    date_range = (
        f"{_format_date(iteration['start'])} – {_format_date(iteration['end'])}"
    )

    lines = [f"## {label} — {date_range}", ""]

    # Goal
    if goal:
        met_marker = {True: "✅", False: "❌", None: ""}[goal_met]
        lines += ["### Goal", "", f"> {goal}", ""]
        if goal_met is not None:
            met_text = (
                "Yes" if goal_met else f"No — {goal_reason}" if goal_reason else "No"
            )
            lines.append(f"**Met:** {met_marker} {met_text}")
            lines.append("")

    lines.append("### Planned")
    for s in delivered + carry_over:
        lines.append(
            f"- @{s.get('assignee', '—')}: "
            f"[#{s['issue_number']}](https://github.com/{repo}/issues/{s['issue_number']}) "
            f"{s['title']} ({s.get('sp', '?')} SP)"
        )

    lines += ["", "### Delivered"]
    if delivered:
        for s in delivered:
            lines.append(
                f"- @{s.get('assignee', '—')}: "
                f"[#{s['issue_number']}](https://github.com/{repo}/issues/{s['issue_number']}) "
                f"{s['title']} ({s.get('sp', '?')} SP)"
            )
    else:
        lines.append("_None_")

    lines += ["", "### Velocity", ""]
    lines.append(
        f"- Planned: **{vel['planned_sp']} SP** · "
        f"Delivered: **{vel['delivered_sp']} SP** · "
        f"Carry-over: **{vel['carry_sp']} SP**"
    )

    if carry_over:
        lines += ["", "### Slip Reasons", ""]
        for slip in slips:
            s = slip["story"]
            note_part = f" — {slip['note']}" if slip["note"] else ""
            lines.append(
                f"- [#{s['issue_number']}](https://github.com/{repo}/issues/{s['issue_number']}) "
                f"{s['title']} — **{slip['code']}**{note_part}"
            )

    if went_well:
        lines += ["", "### What went well", ""]
        for item in went_well:
            lines.append(f"- {item}")

    if to_improve:
        lines += ["", "### What to improve", ""]
        for item in to_improve:
            lines.append(f"- {item}")

    if action_items:
        lines += ["", "### Action items", ""]
        for a in action_items:
            due_part = f" (by {a['due']})" if a["due"] else ""
            lines.append(f"- [ ] @{a['handle']}: {a['action']}{due_part}")

    if notes:
        lines += ["", "### Notes", "", notes]

    lines += ["", "---", ""]
    return "\n".join(lines)


def _update_cumulative_table(text: str, label: str, vel: dict, cumulative: dict) -> str:
    """Replace the cumulative velocity table with an updated version."""
    cum_delivered = cumulative["delivered"] + vel["delivered_sp"]
    cum_planned = cumulative["planned"] + vel["planned_sp"]

    # Build new row
    new_row = (
        f"| {label} "
        f"| {vel['planned_sp']} "
        f"| {vel['delivered_sp']} "
        f"| {cum_delivered} "
        f"| {cum_planned} |"
    )

    # Find the cumulative table and append the row
    table_header = "| Iteration | Planned SP | Delivered SP | Cumulative Delivered | Cumulative Planned |"
    separator = "|---|---|---|---|---|"

    if table_header in text:
        # Find where placeholder row is and replace it, or append after separator
        placeholder_pattern = re.compile(
            r"\| <!-- I\d+ --> \| <!-- N --> \| <!-- N --> \| <!-- N --> \| <!-- N --> \|"
        )
        if placeholder_pattern.search(text):
            text = placeholder_pattern.sub(new_row, text, count=1)
        else:
            # Append new row after the last row in the table
            insert_after = separator
            pos = text.find(insert_after)
            if pos != -1:
                end = pos + len(insert_after)
                # Find end of table block
                text = text[:end] + "\n" + new_row + text[end:]

    return text, cum_delivered, cum_planned


def _insert_iteration_block(text: str, block: str) -> str:
    """Insert the iteration block just before the Cumulative Velocity section."""
    marker = "## Cumulative Velocity"
    pos = text.find(marker)
    if pos != -1:
        return text[:pos] + block + text[pos:]
    # Fallback: append at end
    return text + "\n" + block


# ── Git commit ────────────────────────────────────────────────────────────────


def _git_commit(repo_root: Path, message: str) -> None:
    subprocess.run(
        ["git", "add", "docs/focal/retro-log.md"],
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
    """Log a completed iteration and update docs/focal/retro-log.md."""
    console.print(f"\n[bold cyan]  ◎  Focal — retro ({repo})[/bold cyan]\n")

    state = pm_state.load(repo_root)
    if not state.get("iterations"):
        console.print(
            "[red]No iterations in local state. "
            "Run [bold]focal pm plan[/bold] first.[/red]"
        )
        return

    if refresh:
        console.print("Refreshing state from GitHub...")
        state = pm_state.refresh_from_github(repo_root, repo, config)
        console.print("  [green]✔[/green] State refreshed")

    iteration = _select_iteration(state)
    if not iteration:
        console.print("[red]Invalid selection.[/red]")
        return

    all_stories = pm_state.all_stories(state)
    story_map = {s["id"]: s for s in all_stories}

    console.print(
        f"\nChecking GitHub issue status for {len(iteration['story_ids'])} stories..."
    )
    delivered, carry_over = _check_story_statuses(repo, iteration, story_map)
    console.print(
        f"  [green]✔[/green] Delivered: {len(delivered)} stories · "
        f"Carry-over: {len(carry_over)} stories"
    )

    slips = _prompt_slip_reasons(carry_over)

    goal = iteration.get("goal", "")
    goal_met, goal_reason = _prompt_goal_met(goal)
    went_well = _prompt_bullets("What went well?")
    to_improve = _prompt_bullets("What to improve?")
    action_items = _prompt_action_items()
    notes = Prompt.ask("\nFree-form notes (optional, blank to skip)", default="")

    vel = _velocity(delivered, carry_over, iteration["capacity_sp"])

    retro_path = repo_root / "docs" / "focal" / "retro-log.md"
    if not retro_path.exists():
        console.print(
            "[red]docs/focal/retro-log.md not found. "
            "Run [bold]focal pm init[/bold] first.[/red]"
        )
        return

    text = retro_path.read_text()

    # Derive cumulative from existing table rows
    cum_pattern = re.compile(r"\| I\d+ \| \d+ \| \d+ \| (\d+) \| (\d+) \|")
    all_cum = cum_pattern.findall(text)
    if all_cum:
        last = all_cum[-1]
        cumulative = {"delivered": int(last[0]), "planned": int(last[1])}
    else:
        cumulative = {"delivered": 0, "planned": 0}

    block = _render_iteration_block(
        repo,
        iteration,
        delivered,
        carry_over,
        slips,
        vel,
        goal=goal,
        goal_met=goal_met,
        goal_reason=goal_reason,
        went_well=went_well,
        to_improve=to_improve,
        action_items=action_items,
        notes=notes.strip(),
    )
    text = _insert_iteration_block(text, block)
    text, _, _ = _update_cumulative_table(text, iteration["label"], vel, cumulative)

    retro_path.write_text(text)
    console.print("\n  [green]✔[/green] docs/focal/retro-log.md updated")

    _git_commit(
        repo_root,
        f"chore: retro {iteration['label']} — {vel['delivered_sp']}/{vel['planned_sp']} SP delivered",
    )
    console.print("  [green]✔[/green] Committed")

    console.print(f"\n[bold green]Retro logged — {iteration['label']}[/bold green]")
    console.print(
        f"  Planned: {vel['planned_sp']} SP · "
        f"Delivered: {vel['delivered_sp']} SP · "
        f"Carry-over: {vel['carry_sp']} SP"
    )
    if carry_over:
        console.print(
            f"  [yellow]⚠[/yellow]  {len(carry_over)} stories carry over to next iteration"
        )
