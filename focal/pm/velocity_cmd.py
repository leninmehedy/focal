"""focal pm velocity — show historical velocity from retro-log.md."""

from __future__ import annotations

import re
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table


def run(repo: str, repo_root: Path) -> None:
    retro_log = repo_root / "docs" / "focal" / "retro-log.md"
    if not retro_log.exists():
        Console().print(
            f"[yellow]No retro-log.md found at {retro_log}. "
            "Run `focal pm retro` after your first iteration.[/yellow]"
        )
        raise SystemExit(0)

    rows = _parse_retro_log(retro_log)
    if not rows:
        Console().print(
            "[yellow]retro-log.md exists but contains no completed iteration blocks.[/yellow]"
        )
        raise SystemExit(0)

    console = Console()
    console.print(f"\n[bold]Velocity — {repo}[/bold]\n")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Iter", style="bold cyan")
    table.add_column("Goal", justify="center")
    table.add_column("Capacity", justify="right")
    table.add_column("Planned", justify="right")
    table.add_column("Delivered", justify="right")
    table.add_column("Carry-over", justify="right")
    table.add_column("Efficiency", justify="right")

    total_planned = total_delivered = total_carry = 0
    goal_met_count = 0

    for r in rows:
        planned = r["planned_sp"]
        delivered = r["delivered_sp"]
        carry = r["carry_sp"]
        capacity = r["capacity_sp"]
        efficiency = round(delivered / planned * 100) if planned else 0
        goal_icon = "✅" if r["goal_met"] else "❌"

        total_planned += planned
        total_delivered += delivered
        total_carry += carry
        if r["goal_met"]:
            goal_met_count += 1

        table.add_row(
            r["label"],
            goal_icon,
            f"{capacity} SP",
            f"{planned} SP",
            f"{delivered} SP",
            f"{carry} SP",
            f"{efficiency}%",
        )

    n = len(rows)
    avg_planned = round(total_planned / n) if n else 0
    avg_delivered = round(total_delivered / n) if n else 0
    avg_carry = round(total_carry / n) if n else 0
    avg_efficiency = (
        round(total_delivered / total_planned * 100) if total_planned else 0
    )

    table.add_section()
    table.add_row(
        "Avg",
        "",
        "",
        f"{avg_planned} SP",
        f"{avg_delivered} SP",
        f"{avg_carry} SP",
        f"{avg_efficiency}%",
        style="dim",
    )

    console.print(table)
    console.print(
        f"{n} iteration{'s' if n != 1 else ''}  ·  "
        f"{total_delivered} SP delivered  ·  "
        f"avg carry-over: {avg_carry} SP/iter\n"
    )


def _parse_retro_log(path: Path) -> list[dict]:
    """Return list of {label, capacity_sp, planned_sp, delivered_sp, carry_sp, goal_met}."""
    text = path.read_text(encoding="utf-8")
    # Split on iteration headings
    raw_blocks = re.split(r"\n(?=## )", text)

    rows: list[dict] = []
    for block in raw_blocks:
        heading_match = re.match(r"## (I\d+)\s+[—–-]", block)
        if not heading_match:
            continue
        label = heading_match.group(1)

        kv = dict(re.findall(r"\|\s*\*\*(.*?)\*\*\s*\|\s*(.*?)\s*\|", block))

        def _sp(key: str) -> int:
            val = kv.get(key, "")
            m = re.search(r"(\d+)\s*SP", val)
            return int(m.group(1)) if m else 0

        goal_met_val = kv.get("Goal met", "")
        goal_met = bool(re.search(r"yes", goal_met_val, re.IGNORECASE))

        rows.append(
            {
                "label": label,
                "capacity_sp": _sp("Capacity"),
                "planned_sp": _sp("Planned"),
                "delivered_sp": _sp("Delivered"),
                "carry_sp": _sp("Carry-over"),
                "goal_met": goal_met,
            }
        )

    return rows
