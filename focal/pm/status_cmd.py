"""focal pm status — live terminal summary of the current iteration."""

from datetime import date
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn

from . import pm_state

console = Console()


def _current_iteration(state: dict) -> dict | None:
    today = date.today()
    for it in state.get("iterations", []):
        start = date.fromisoformat(it["start"])
        end = date.fromisoformat(it["end"])
        if start <= today <= end:
            return it
    # Fall back to the last iteration if we're past all of them
    iters = state.get("iterations", [])
    return iters[-1] if iters else None


def _days_remaining(iteration: dict) -> int:
    end = date.fromisoformat(iteration["end"])
    delta = (end - date.today()).days
    return max(0, delta)


def _project_delivery(
    delivered_sp: int, total_sp: int, days_remaining: int, total_days: int
) -> int:
    if total_days <= 0 or total_sp <= 0:
        return delivered_sp
    days_elapsed = total_days - days_remaining
    if days_elapsed <= 0:
        return 0
    rate = delivered_sp / days_elapsed
    projected = delivered_sp + rate * days_remaining
    return min(round(projected), total_sp)


def run(repo: str, repo_root: Path, config: dict, refresh: bool = False) -> None:
    """Print a live terminal summary of the current iteration."""
    console.print(f"\n[bold cyan]  ◎  Focal — status ({repo})[/bold cyan]\n")

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
        console.print("  [green]✔[/green] State refreshed\n")

    iteration = _current_iteration(state)
    if not iteration:
        console.print("[red]No current iteration found.[/red]")
        return

    all_stories = pm_state.all_stories(state)
    story_map = {s["id"]: s for s in all_stories}

    # Bucket stories by project_status / GitHub state
    planned_stories = [
        story_map[sid] for sid in iteration["story_ids"] if sid in story_map
    ]

    delivered, in_progress, blocked, not_started = [], [], [], []
    for s in planned_stories:
        st = s.get("status", "open")
        ps = s.get("project_status", "").lower()
        if st == "closed":
            delivered.append(s)
        elif "blocked" in ps or "✋" in ps:
            blocked.append(s)
        elif "progress" in ps or "review" in ps:
            in_progress.append(s)
        else:
            not_started.append(s)

    delivered_sp = sum(s.get("sp", 0) for s in delivered)
    in_progress_sp = sum(s.get("sp", 0) for s in in_progress)
    blocked_sp = sum(s.get("sp", 0) for s in blocked)
    not_started_sp = sum(s.get("sp", 0) for s in not_started)
    total_sp = delivered_sp + in_progress_sp + blocked_sp + not_started_sp

    start_d = date.fromisoformat(iteration["start"])
    end_d = date.fromisoformat(iteration["end"])
    total_days = (end_d - start_d).days + 1
    days_rem = _days_remaining(iteration)
    projected_sp = _project_delivery(delivered_sp, total_sp, days_rem, total_days)

    pct = int(delivered_sp / total_sp * 100) if total_sp else 0
    proj_pct = int(projected_sp / total_sp * 100) if total_sp else 0

    # ── Header ────────────────────────────────────────────────────────────────
    start_fmt = start_d.strftime("%b %-d")
    end_fmt = end_d.strftime("%b %-d")
    console.print(
        f"[bold]Focal Board — {iteration['label']} ({start_fmt} – {end_fmt})[/bold]"
    )
    console.rule()

    # ── Progress bar ──────────────────────────────────────────────────────────
    with Progress(
        TextColumn("  {task.description:<14}"),
        BarColumn(bar_width=24, complete_style="green", finished_style="green"),
        TextColumn("{task.fields[label]}"),
        console=console,
        expand=False,
    ) as progress:
        progress.add_task(
            "Delivered",
            total=total_sp or 1,
            completed=delivered_sp,
            label=f"{delivered_sp} / {total_sp} SP ({pct}%)",
        )

    # ── Story breakdown ───────────────────────────────────────────────────────
    def _story_line(label: str, stories: list, sp: int, style: str) -> None:
        count = len(stories)
        noun = "story" if count == 1 else "stories"
        console.print(f"  [{style}]{label:<14}[/{style}]  {count} {noun} · {sp} SP")

    _story_line("In progress", in_progress, in_progress_sp, "cyan")
    _story_line("Blocked", blocked, blocked_sp, "red")
    _story_line("Not started", not_started, not_started_sp, "dim")

    console.print()
    console.print(f"  [dim]Days remaining:[/dim]  {days_rem}")
    console.print(f"  [dim]Projected:[/dim]       {projected_sp} SP ({proj_pct}%)")

    if refresh:
        from datetime import datetime

        ts = state.get("last_synced", "")
        if ts:
            dt = datetime.fromisoformat(ts).astimezone()
            console.print(
                f"\n  [dim]Last synced: {dt.strftime('%b %-d %H:%M %Z')}[/dim]"
            )

    console.print()

    # ── Blocked detail ────────────────────────────────────────────────────────
    if blocked:
        console.print("[bold red]Blocked stories:[/bold red]")
        for s in blocked:
            console.print(
                f"  #{s['issue_number']} {s['title']} "
                f"(@{s.get('assignee', '—')}) · {s.get('sp', '?')} SP"
            )
        console.print()

    # ── Active design docs ────────────────────────────────────────────────────
    from . import design_cmd

    active_designs = design_cmd.summary_lines(repo_root)
    if active_designs:
        console.print("[bold]Design docs[/bold]")
        for line in active_designs:
            console.print(f"  [dim]{line}[/dim]")
        console.print()
