"""Parse docs/focal/plan.md into structured epic/story data for adopt-plan."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ## E2 — Title · ~8 SP   or   ## E0 — General Maintenance · ~ongoing
_EPIC_RE = re.compile(
    r"^## (E\w+) — (.+?) · ~(\d+|ongoing)(?: SP)?",
    re.MULTILINE,
)

# | **2.1** — Title | 5 | notes |
_STORY_RE = re.compile(
    r"^\| \*\*(\d+\.\w+)\*\* — (.+?) \| (\d+) \|",
    re.MULTILINE,
)

# Repository: `owner/repo`
_REPO_RE = re.compile(r"^Repository:\s*`([^`]+)`", re.MULTILINE)


@dataclass
class ParsedStory:
    local_id: str  # "2.1"
    title: str
    sp: int
    notes: str = ""


@dataclass
class ParsedEpic:
    local_id: str  # "E2"
    title: str
    sp: int | None  # None means "ongoing"
    stories: list[ParsedStory] = field(default_factory=list)


@dataclass
class ParsedPlanDoc:
    repo: str | None
    epics: list[ParsedEpic]


def parse(path: Path) -> ParsedPlanDoc:
    """Parse a plan.md file and return structured epic/story data."""
    text = path.read_text()

    repo_match = _REPO_RE.search(text)
    repo = repo_match.group(1) if repo_match else None

    # Find all epic headings and their byte offsets so we can extract the
    # story rows that fall under each epic section.
    epic_matches = list(_EPIC_RE.finditer(text))
    epics: list[ParsedEpic] = []

    for i, em in enumerate(epic_matches):
        local_id = em.group(1)
        title = em.group(2).strip()
        raw_sp = em.group(3)
        sp = None if raw_sp == "ongoing" else int(raw_sp)

        # Section text runs from end of this heading to start of next (or EOF)
        section_start = em.end()
        section_end = (
            epic_matches[i + 1].start() if i + 1 < len(epic_matches) else len(text)
        )
        section = text[section_start:section_end]

        stories = [
            ParsedStory(
                local_id=sm.group(1),
                title=sm.group(2).strip(),
                sp=int(sm.group(3)),
            )
            for sm in _STORY_RE.finditer(section)
        ]

        epics.append(ParsedEpic(local_id=local_id, title=title, sp=sp, stories=stories))

    return ParsedPlanDoc(repo=repo, epics=epics)
