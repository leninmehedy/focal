"""Shared planning helpers used by plan_cmd and whatif_cmd."""

import copy
from datetime import date, timedelta


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def iter_end(start: date, weeks: int) -> date:
    return start + timedelta(weeks=weeks) - timedelta(days=1)


def format_date(d: date) -> str:
    return d.strftime("%b %-d")


def assign_stories_to_iters(stories: list[dict], iters: list[dict]) -> list[dict]:
    """Greedily pack open stories into iterations by SP capacity.

    Returns a deep copy of *iters* with story_ids populated.
    Does not mutate the inputs.
    """
    iters = copy.deepcopy(iters)
    open_stories = [s for s in stories if s.get("status") != "closed"]
    open_stories.sort(
        key=lambda s: (s.get("sp", 0) == 0, s.get("epic_id", ""), s["id"])
    )

    remaining = list(open_stories)
    for it in iters:
        budget = it["capacity_sp"]
        assigned = []
        leftover = []
        for story in remaining:
            sp = story.get("sp", 0)
            if sp <= budget:
                assigned.append(story["id"])
                budget -= sp
            else:
                leftover.append(story)
        it["story_ids"] = assigned
        remaining = leftover
        if not remaining:
            break

    return iters
