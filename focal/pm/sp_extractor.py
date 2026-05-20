"""SP extraction from multiple sources, in priority order.

Priority:
  1. GitHub Projects custom field (caller provides pre-fetched value)
  2. Title pattern:  [13]  or  (13 SP)  or  13SP
  3. Body table row: | SP | 13 |  or  | Story Points | 13 |
  4. None — caller emits a warning
"""

import re
from typing import Optional

# Matches: [13]  (13)  (13 SP)  13SP  #13SP
_TITLE_PATTERNS = [
    re.compile(r"\[(\d+)\]"),
    re.compile(r"\((\d+)\s*SP\)", re.IGNORECASE),
    re.compile(r"#?(\d+)\s*SP\b", re.IGNORECASE),
]

# Matches table rows like:  | SP | 13 |  or  | Story Points | 13 |
_BODY_TABLE_RE = re.compile(
    r"^\|\s*(?:SP|Story\s+Points)\s*\|\s*(\d+)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)

# Matches prose like:  **Estimated:** 5 SP  or  Estimated: 5 SP
_BODY_PROSE_RE = re.compile(
    r"\*{0,2}Estimated:?\*{0,2}\s*(\d+)\s*SP",
    re.IGNORECASE,
)


def _from_title(title: str) -> Optional[int]:
    for pattern in _TITLE_PATTERNS:
        m = pattern.search(title)
        if m:
            return int(m.group(1))
    return None


def _from_body_table(body: str) -> Optional[int]:
    m = _BODY_TABLE_RE.search(body)
    return int(m.group(1)) if m else None


def _from_body_prose(body: str) -> Optional[int]:
    m = _BODY_PROSE_RE.search(body)
    return int(m.group(1)) if m else None


def extract_sp(
    issue: dict,
    project_field_value: Optional[int] = None,
) -> Optional[int]:
    """Return SP for *issue*, trying sources in priority order.

    Args:
        issue: dict with at least 'title' and 'body' keys.
        project_field_value: pre-fetched GitHub Projects custom field value,
            or None if not available / not applicable.

    Returns:
        SP as int, or None if no estimate could be found.
    """
    # 1. GitHub Projects field — most authoritative
    if project_field_value is not None:
        return project_field_value

    # 2. Title pattern
    sp = _from_title(issue.get("title", ""))
    if sp is not None:
        return sp

    body = issue.get("body", "")

    # 3. Body table
    sp = _from_body_table(body)
    if sp is not None:
        return sp

    # 4. Body prose: **Estimated:** N SP
    sp = _from_body_prose(body)
    if sp is not None:
        return sp

    return None
