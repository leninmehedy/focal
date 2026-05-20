"""Determine parent/child relationships between epics and stories.

Resolution priority:
  1. GitHub sub-issues API (authoritative)
  2. Body mention:  "Part of #N"  /  "Parent: #N"  /  "Parent #N"
  3. Title prefix:  "[Epic N]"  /  "E1:"
  4. Orphaned — no parent found; caller adds as top-level orphan
"""

import re
from typing import Optional

_BODY_PARENT_RE = re.compile(
    r"(?:Part\s+of(?:\s+epic)?|Parent:?)\s+#(\d+)",
    re.IGNORECASE,
)

_TITLE_PREFIX_RE = re.compile(
    r"(?:\[Epic\s*(\d+)\]|E(\d+):)",
    re.IGNORECASE,
)


def _parent_from_body(body: str) -> Optional[int]:
    m = _BODY_PARENT_RE.search(body)
    return int(m.group(1)) if m else None


def _parent_from_title(title: str) -> Optional[int]:
    m = _TITLE_PREFIX_RE.search(title)
    if m:
        return int(m.group(1) or m.group(2))
    return None


def resolve(
    epics: list[dict],
    stories: list[dict],
    sub_issue_map: dict[int, list[int]],
) -> dict[int, Optional[int]]:
    """Return a mapping of story issue_number → parent epic issue_number (or None).

    Args:
        epics: list of epic issue dicts (must have 'number').
        stories: list of story issue dicts (must have 'number', 'title', 'body').
        sub_issue_map: {epic_number: [child_issue_numbers]} from the sub-issues API.

    Returns:
        {story_number: epic_number | None}
        None means orphaned — no parent found.
    """
    epic_numbers = {e["number"] for e in epics}

    # Build reverse map from sub-issues API: child → parent
    api_parent: dict[int, int] = {}
    for epic_num, children in sub_issue_map.items():
        if epic_num in epic_numbers:
            for child in children:
                api_parent[child] = epic_num

    result: dict[int, Optional[int]] = {}
    for story in stories:
        num = story["number"]

        # 1. Sub-issues API
        if num in api_parent:
            result[num] = api_parent[num]
            continue

        # 2. Body mention
        parent = _parent_from_body(story.get("body", ""))
        if parent and parent in epic_numbers:
            result[num] = parent
            continue

        # 3. Title prefix
        parent = _parent_from_title(story.get("title", ""))
        if parent and parent in epic_numbers:
            result[num] = parent
            continue

        # 4. Orphaned
        result[num] = None

    return result
