"""Parse the ## Breakdown hint section from a Focal design doc.

Expected format:

    ## Breakdown hint

    Epic: <title> (~N SP)
      - Story: <title> (N SP)
      - Story: <title> (N SP)
"""

import re
from pathlib import Path
from typing import Optional

_EPIC_RE = re.compile(r"^Epic:\s+(.+?)\s+\(~?(\d+)\s*SP\)\s*$", re.IGNORECASE)
_STORY_RE = re.compile(r"^\s+-\s+Story:\s+(.+?)\s+\((\d+)\s*SP\)\s*$", re.IGNORECASE)


def parse(path: Path) -> Optional[dict]:
    """Return parsed breakdown from *path*, or None if no Breakdown hint section.

    Returns:
        {
            "epic_title": str,
            "epic_sp": int,
            "stories": [{"title": str, "sp": int}, ...],
        }
    """
    text = path.read_text(encoding="utf-8")
    # Find the ## Breakdown hint section
    m = re.search(
        r"^## Breakdown hint\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    if not m:
        return None

    section = m.group(1)
    epic_title: Optional[str] = None
    epic_sp: int = 0
    stories: list[dict] = []

    for line in section.splitlines():
        em = _EPIC_RE.match(line.strip())
        if em:
            epic_title = em.group(1).strip()
            epic_sp = int(em.group(2))
            continue
        sm = _STORY_RE.match(line)
        if sm:
            stories.append({"title": sm.group(1).strip(), "sp": int(sm.group(2))})

    if epic_title is None:
        return None

    return {"epic_title": epic_title, "epic_sp": epic_sp, "stories": stories}
