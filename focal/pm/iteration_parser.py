"""Parse docs/focal/iteration-planning.md into structured data for what-if simulation."""

import re
from pathlib import Path
from typing import Optional

_ITER_HEADER_RE = re.compile(
    r"^### (I\d+) — ([\d\-]+ – [\d\-]+|\w+ \d+ – \w+ \d+) · (\d+) SP",
    re.MULTILINE,
)
_STORY_ROW_RE = re.compile(
    r"^\| \[([^\]]+)\]\([^)]+\) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| @?([^|]+) \|",
    re.MULTILINE,
)
_TEAM_ROW_RE = re.compile(r"^\| @(\w+) \| (\d+) \|", re.MULTILINE)
_ITER_LENGTH_RE = re.compile(r"\| Length \| (\d+) weeks \|")
_START_DATE_RE = re.compile(r"\| Start date \| ([\d\-]+) \|")


def load(path: Path) -> Optional[dict]:
    """Parse iteration-planning.md and return structured plan data.

    Returns:
        {
            "weeks": int,
            "start": "YYYY-MM-DD",
            "members": [{"handle": str, "sp_per_iter": int}],
            "iterations": [
                {
                    "label": "I1",
                    "start": "YYYY-MM-DD",   # approximate from header
                    "end": "YYYY-MM-DD",
                    "capacity_sp": int,
                    "story_ids": [str],
                    "notes": [],
                }
            ],
        }
        Returns None if the file does not exist or cannot be parsed.
    """
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")

    # Team members + capacity
    members = [
        {"handle": m.group(1), "sp_per_iter": int(m.group(2))}
        for m in _TEAM_ROW_RE.finditer(text)
    ]

    # Iteration length and start
    weeks = 2
    wm = _ITER_LENGTH_RE.search(text)
    if wm:
        weeks = int(wm.group(1))

    start = None
    sm = _START_DATE_RE.search(text)
    if sm:
        start = sm.group(1)

    # Parse iteration sections
    iterations = []
    iter_matches = list(_ITER_HEADER_RE.finditer(text))
    for i, m in enumerate(iter_matches):
        label = m.group(1)
        capacity_sp = int(m.group(3))
        section_start = m.end()
        section_end = (
            iter_matches[i + 1].start() if i + 1 < len(iter_matches) else len(text)
        )
        section = text[section_start:section_end]

        story_ids = [sm.group(1).strip() for sm in _STORY_ROW_RE.finditer(section)]

        iterations.append(
            {
                "label": label,
                "start": "",
                "end": "",
                "capacity_sp": capacity_sp,
                "story_ids": story_ids,
                "notes": [],
            }
        )

    return {
        "weeks": weeks,
        "start": start or "",
        "members": members,
        "iterations": iterations,
    }
