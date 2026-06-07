"""focal pm what-if — dry-run simulation of iteration plan under hypothetical scenarios.

Scenarios:
  --pto HANDLE:FROM:TO        Reduce capacity for a team member over a date range.
  --inject "TITLE:SP"         Inject a high-priority story into the current iteration.
  --reestimate STORY_ID:SP    Update an existing story's SP and ripple through the plan.

Dry-run by default. Pass --apply to write the updated iteration-planning.md.
"""

import copy
import subprocess
from datetime import date, timedelta
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import pm_state
from .iteration_parser import load as load_plan
from .plan_helpers import assign_stories_to_iters, parse_date

console = Console()


# ── Scenario parsing ──────────────────────────────────────────────────────────


def _parse_pto(raw: list[str]) -> list[dict]:
    """Parse ["handle:YYYY-MM-DD:YYYY-MM-DD", ...] into dicts."""
    result = []
    for entry in raw:
        parts = entry.split(":")
        if len(parts) != 3:
            raise ValueError(f"--pto format must be HANDLE:FROM:TO (got '{entry}')")
        handle, from_s, to_s = parts
        result.append(
            {
                "handle": handle.strip().lstrip("@"),
                "from": parse_date(from_s.strip()),
                "to": parse_date(to_s.strip()),
            }
        )
    return result


def _parse_inject(raw: list[str]) -> list[dict]:
    """Parse ["Title:SP", ...] into dicts."""
    result = []
    for entry in raw:
        if ":" not in entry:
            raise ValueError(f"--inject format must be TITLE:SP (got '{entry}')")
        title, _, sp_s = entry.rpartition(":")
        try:
            sp = int(sp_s.strip())
        except ValueError:
            raise ValueError(f"--inject SP must be an integer (got '{sp_s}')")
        result.append({"title": title.strip(), "sp": sp})
    return result


def _parse_reestimate(raw: list[str]) -> list[dict]:
    """Parse ["STORY_ID:SP", ...] into dicts."""
    result = []
    for entry in raw:
        if ":" not in entry:
            raise ValueError(f"--reestimate format must be STORY_ID:SP (got '{entry}')")
        story_id, _, sp_s = entry.rpartition(":")
        try:
            sp = int(sp_s.strip())
        except ValueError:
            raise ValueError(f"--reestimate SP must be an integer (got '{sp_s}')")
        result.append({"story_id": story_id.strip(), "new_sp": sp})
    return result


# ── Scenario application ──────────────────────────────────────────────────────


def _working_days_overlap(
    from_d: date, to_d: date, iter_start: str, iter_end: str
) -> int:
    """Count working days (Mon–Fri) in the overlap of [from_d, to_d] and [iter_start, iter_end]."""
    if not iter_start or not iter_end:
        return 0
    i_start = parse_date(iter_start)
    i_end = parse_date(iter_end)
    overlap_start = max(from_d, i_start)
    overlap_end = min(to_d, i_end)
    if overlap_start > overlap_end:
        return 0
    days = 0
    d = overlap_start
    while d <= overlap_end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days


def _apply_pto(
    iters: list[dict], members: list[dict], pto_list: list[dict]
) -> list[dict]:
    """Reduce iteration capacity for PTO periods. Returns modified iters."""
    iters = copy.deepcopy(iters)
    for pto in pto_list:
        member = next((m for m in members if m["handle"] == pto["handle"]), None)
        if member is None:
            continue
        sp_per_day = member["sp_per_iter"] / 10  # assume 2-week iter = 10 working days
        for it in iters:
            overlap = _working_days_overlap(
                pto["from"], pto["to"], it.get("start", ""), it.get("end", "")
            )
            if overlap:
                reduction = round(sp_per_day * overlap)
                it["capacity_sp"] = max(0, it["capacity_sp"] - reduction)
                it.setdefault("notes", []).append(
                    f"@{pto['handle']} PTO {pto['from']} – {pto['to']} "
                    f"(−{reduction} SP)"
                )
    return iters


def _apply_inject(stories: list[dict], inject_list: list[dict]) -> list[dict]:
    """Prepend injected stories to the open backlog with a synthetic ID."""
    stories = copy.deepcopy(stories)
    for i, inj in enumerate(inject_list):
        stories.insert(
            0,
            {
                "id": f"INJ{i + 1}",
                "title": inj["title"],
                "sp": inj["sp"],
                "epic_id": "",
                "issue_number": "",
                "assignee": "",
                "status": "open",
                "project_status": "",
                "_injected": True,
            },
        )
    return stories


def _apply_reestimate(stories: list[dict], reestimate_list: list[dict]) -> list[dict]:
    """Update SP for matching stories. Returns modified stories."""
    stories = copy.deepcopy(stories)
    id_map = {s["id"]: s for s in stories}
    for re in reestimate_list:
        if re["story_id"] in id_map:
            id_map[re["story_id"]]["sp"] = re["new_sp"]
            id_map[re["story_id"]]["_reestimated"] = True
    return stories


# ── Diff engine ───────────────────────────────────────────────────────────────


def _diff_plans(original_iters: list[dict], simulated_iters: list[dict]) -> list[dict]:
    """Compare two iteration plans and return per-iteration diff entries."""
    orig_map = {it["label"]: set(it["story_ids"]) for it in original_iters}
    sim_map = {it["label"]: set(it["story_ids"]) for it in simulated_iters}
    all_labels = list(
        dict.fromkeys(
            [it["label"] for it in original_iters]
            + [it["label"] for it in simulated_iters]
        )
    )

    diffs = []
    for label in all_labels:
        orig_ids = orig_map.get(label, set())
        sim_ids = sim_map.get(label, set())
        slipped_out = orig_ids - sim_ids  # were here, now gone
        added_in = sim_ids - orig_ids  # new arrivals (injected or carried in)
        diffs.append(
            {
                "label": label,
                "orig_count": len(orig_ids),
                "sim_count": len(sim_ids),
                "slipped_out": sorted(slipped_out),
                "added_in": sorted(added_in),
                "changed": slipped_out or added_in,
            }
        )
    return diffs


# ── Impact report renderer ────────────────────────────────────────────────────


def _render_report(
    repo: str,
    scenario: dict,
    original_iters: list[dict],
    simulated_iters: list[dict],
    all_stories: list[dict],
    diffs: list[dict],
) -> None:
    story_map = {s["id"]: s for s in all_stories}

    console.print(f"\n[bold cyan]  ◎  Focal — what-if ({repo})[/bold cyan]\n")

    # Scenario summary
    console.print("[bold]Scenario[/bold]")
    if scenario.get("pto"):
        for p in scenario["pto"]:
            console.print(f"  PTO  @{p['handle']}  {p['from']} – {p['to']}")
    if scenario.get("inject"):
        for inj in scenario["inject"]:
            console.print(
                f"  Inject  '{inj['title']}'  {inj['sp']} SP"
                "  [dim](track under E0 General Maintenance)[/dim]"
            )
    if scenario.get("reestimate"):
        for re in scenario["reestimate"]:
            orig_sp = story_map.get(re["story_id"], {}).get("sp", "?")
            console.print(
                f"  Re-estimate  {re['story_id']}:  {orig_sp} SP → {re['new_sp']} SP"
            )

    # Per-iteration diff table
    console.print("\n[bold]Impact by iteration[/bold]")
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Iter", width=5)
    table.add_column("Orig SP", justify="right", width=8)
    table.add_column("Sim SP", justify="right", width=7)
    table.add_column("Cap", justify="right", width=5)
    table.add_column("Slipped out", style="red")
    table.add_column("Added in", style="green")

    sim_cap_map = {it["label"]: it["capacity_sp"] for it in simulated_iters}
    orig_sp_map = {
        it["label"]: sum(story_map.get(sid, {}).get("sp", 0) for sid in it["story_ids"])
        for it in original_iters
    }
    sim_sp_map = {
        it["label"]: sum(story_map.get(sid, {}).get("sp", 0) for sid in it["story_ids"])
        for it in simulated_iters
    }

    changed_iters = 0
    for diff in diffs:
        label = diff["label"]
        orig_sp = orig_sp_map.get(label, 0)
        sim_sp = sim_sp_map.get(label, 0)
        cap = sim_cap_map.get(label, "—")
        slipped = ", ".join(diff["slipped_out"]) or "—"
        added = ", ".join(diff["added_in"]) or "—"
        row_style = "bold" if diff["changed"] else "dim"
        table.add_row(
            label,
            str(orig_sp),
            str(sim_sp),
            str(cap),
            slipped,
            added,
            style=row_style if diff["changed"] else None,
        )
        if diff["changed"]:
            changed_iters += 1

    console.print(table)

    # Summary
    total_slipped = sum(len(d["slipped_out"]) for d in diffs)
    total_added = sum(len(d["added_in"]) for d in diffs)
    console.print("\n[bold]Summary[/bold]")
    if total_slipped == 0 and total_added == 0:
        console.print("  [green]No stories affected — plan unchanged.[/green]")
    else:
        if total_slipped:
            console.print(
                f"  [red]{total_slipped} story slot(s) slipped[/red] across {changed_iters} iteration(s)"
            )
        if total_added:
            console.print(
                f"  [green]{total_added} story slot(s) gained[/green] (injections / carry-ins)"
            )

    # Notes from PTO-reduced iterations
    notes = [(it["label"], n) for it in simulated_iters for n in it.get("notes", [])]
    if notes:
        console.print("\n[bold]Capacity changes[/bold]")
        for label, note in notes:
            console.print(f"  {label}  [yellow]{note}[/yellow]")


# ── Apply (write updated plan) ────────────────────────────────────────────────


def _write_plan(
    repo_root: Path, repo: str, simulated_iters: list[dict], all_stories: list[dict]
) -> None:
    from .plan_cmd import _render as render_plan

    # Build minimal members list from simulated iters (capacity already baked in)
    # We re-use the existing renderer via a synthetic members list
    members = (
        [{"handle": "team", "sp_per_iter": simulated_iters[0]["capacity_sp"]}]
        if simulated_iters
        else []
    )

    content = render_plan(
        repo=repo,
        members=members,
        iters=simulated_iters,
        risks=[],
        all_stories=all_stories,
        weeks=2,
    )
    plan_path = repo_root / "docs" / "focal" / "iteration-planning.md"
    plan_path.write_text(content, encoding="utf-8")
    subprocess.run(
        ["git", "add", str(plan_path)],
        cwd=repo_root,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "chore: apply what-if simulation to iteration-planning.md",
        ],
        cwd=repo_root,
        capture_output=True,
    )
    console.print(f"\n  [green]✔[/green] {plan_path} updated and committed")


# ── Main entry point ──────────────────────────────────────────────────────────


def run(
    repo: str,
    repo_root: Path,
    pto_raw: list[str],
    inject_raw: list[str],
    reestimate_raw: list[str],
    apply: bool,
) -> None:
    # Parse scenario flags
    try:
        pto_list = _parse_pto(pto_raw)
        inject_list = _parse_inject(inject_raw)
        reestimate_list = _parse_reestimate(reestimate_raw)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return

    if not pto_list and not inject_list and not reestimate_list:
        console.print(
            "[yellow]No scenario specified. Use --pto, --inject, or --reestimate.[/yellow]"
        )
        return

    scenario = {"pto": pto_list, "inject": inject_list, "reestimate": reestimate_list}

    # Load current plan
    plan_path = repo_root / "docs" / "focal" / "iteration-planning.md"
    plan = load_plan(plan_path)
    if plan is None:
        console.print(
            f"[red]No iteration plan found at {plan_path}. "
            "Run [bold]focal pm plan[/bold] first.[/red]"
        )
        return

    # Load stories from state cache
    state = pm_state.load(repo_root)
    all_stories: list[dict] = []
    for epic in state.get("epics", []):
        epic_id = epic.get("id", "")
        for s in epic.get("stories", []):
            all_stories.append({**s, "epic_id": epic_id})

    if not all_stories:
        console.print(
            "[red]No stories in local state cache. Run focal cache refresh.[/red]"
        )
        return

    original_iters = plan["iterations"]
    members = plan["members"]

    # Apply scenarios to get simulated state
    sim_iters = copy.deepcopy(original_iters)
    sim_stories = copy.deepcopy(all_stories)

    if pto_list:
        sim_iters = _apply_pto(sim_iters, members, pto_list)
    if inject_list:
        sim_stories = _apply_inject(sim_stories, inject_list)
    if reestimate_list:
        sim_stories = _apply_reestimate(sim_stories, reestimate_list)

    # Re-run greedy assignment on modified data
    sim_iters = assign_stories_to_iters(sim_stories, sim_iters)
    orig_iters_assigned = assign_stories_to_iters(all_stories, original_iters)

    # Diff and render
    diffs = _diff_plans(orig_iters_assigned, sim_iters)
    _render_report(repo, scenario, orig_iters_assigned, sim_iters, sim_stories, diffs)

    if apply:
        _write_plan(repo_root, repo, sim_iters, sim_stories)
    else:
        console.print(
            "\n  [dim]Dry run — pass --apply to write updated iteration-planning.md[/dim]"
        )
