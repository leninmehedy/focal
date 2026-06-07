"""Render docs/focal/epics.md from focal-state.json.

focal owns this file completely. It is re-rendered on every mutating PM command.
Humans should not edit it — the <!-- focal-managed --> header says so.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

_STATUS_ICON = {
    "open": "🔄",
    "closed": "✅",
    "": "📋",
}

_HEADER = """\
<!-- focal-managed: do not edit manually — re-rendered from focal-state.json -->
# Epics & Stories

_Last updated: {today}_

---
"""


def render(repo_root: Path, state: dict) -> None:
    """Re-render docs/focal/epics.md from state. Atomic write."""
    epics_path = repo_root / "docs" / "focal" / "epics.md"
    epics_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [_HEADER.format(today=date.today())]

    for epic in state.get("epics", []):
        sp = epic.get("sp")
        sp_label = (
            "ongoing"
            if sp == 0 and epic.get("id") == "E0"
            else (f"{sp} SP" if sp else "? SP")
        )
        issue_number = epic.get("issue_number")
        repo = state.get("repo", "")
        issue_link = (
            f"[#{issue_number}](https://github.com/{repo}/issues/{issue_number})"
            if issue_number
            else "no issue"
        )
        lines.append(f"## {epic['id']} — {epic['title']} · {issue_link} · {sp_label}\n")
        lines.append("")

        stories = epic.get("stories", [])
        if stories:
            lines.append("| Story | GitHub | SP | Status |")
            lines.append("|---|---|---|---|")
            for s in stories:
                s_num = s.get("issue_number")
                s_link = (
                    f"[#{s_num}](https://github.com/{repo}/issues/{s_num})"
                    if s_num
                    else "—"
                )
                s_sp = s.get("sp", "?")
                s_icon = _STATUS_ICON.get(s.get("status", ""), "📋")
                lines.append(
                    f"| **{s['id']}** — {s['title']} | {s_link} | {s_sp} | {s_icon} |"
                )
            lines.append("")
        else:
            lines.append("| Story | GitHub | SP | Status |")
            lines.append("|---|---|---|---|")
            lines.append("")

        lines.append("---")
        lines.append("")

    content = "\n".join(lines)

    # Atomic write
    tmp = tempfile.NamedTemporaryFile(
        mode="w", dir=epics_path.parent, delete=False, suffix=".tmp"
    )
    try:
        tmp.write(content)
        tmp.flush()
        tmp.close()
        Path(tmp.name).replace(epics_path)
    except Exception:
        Path(tmp.name).unlink(missing_ok=True)
        raise
