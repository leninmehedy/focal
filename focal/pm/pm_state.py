"""Local metadata cache for focal pm — docs/focal/.focal-state.json.

GitHub is always authoritative. This file is a cache that lets plan,
retro, and status work without making dozens of API calls every run.

Schema:
{
  "repo": "owner/repo",
  "last_synced": "ISO-8601",
  "epics": [
    {
      "id": "E1",
      "title": "...",
      "issue_number": 25,
      "issue_url": "...",
      "issue_db_id": 123456789,
      "sp": 44,
      "status": "open",
      "stories": [
        {
          "id": "1.1",
          "title": "...",
          "issue_number": 26,
          "issue_url": "...",
          "issue_db_id": 123456790,
          "sp": 8,
          "assignee": "leninmehedy",
          "status": "open",
          "project_status": "In progress"
        }
      ]
    }
  ],
  "iterations": [
    {
      "number": 1,
      "label": "I1",
      "start": "2026-05-18",
      "end": "2026-05-31",
      "capacity_sp": 22,
      "story_ids": ["1.1", "1.2"]
    }
  ]
}
"""

import json
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIR = ".cache"
STATE_FILE = "focal-state.json"


def state_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "focal" / CACHE_DIR / STATE_FILE


def load(repo_root: Path) -> dict:
    path = state_path(repo_root)
    if not path.exists():
        return {"repo": "", "last_synced": None, "epics": [], "iterations": []}
    with open(path) as f:
        return json.load(f)


def save(repo_root: Path, state: dict) -> None:
    path = state_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["last_synced"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def upsert_epic(state: dict, epic: dict) -> None:
    """Add or update an epic entry by ID."""
    for i, e in enumerate(state["epics"]):
        if e["id"] == epic["id"]:
            # Preserve existing stories
            epic.setdefault("stories", e.get("stories", []))
            state["epics"][i] = epic
            return
    epic.setdefault("stories", [])
    state["epics"].append(epic)


def upsert_story(state: dict, epic_id: str, story: dict) -> None:
    """Add or update a story under the given epic."""
    for epic in state["epics"]:
        if epic["id"] == epic_id:
            for i, s in enumerate(epic["stories"]):
                if s["id"] == story["id"]:
                    epic["stories"][i] = story
                    return
            epic["stories"].append(story)
            return


def get_epic(state: dict, epic_id: str) -> dict | None:
    return next((e for e in state["epics"] if e["id"] == epic_id), None)


def all_stories(state: dict) -> list[dict]:
    """Flat list of all stories across all epics, with epic_id injected."""
    result = []
    for epic in state["epics"]:
        for story in epic.get("stories", []):
            result.append({**story, "epic_id": epic["id"], "epic_title": epic["title"]})
    return result


def refresh_from_github(repo_root: Path, repo: str, config: dict) -> dict:
    """Re-fetch all epic/story state from GitHub and overwrite local cache.

    Uses batched GraphQL (100 issues per round-trip) instead of one gh CLI
    call per issue, reducing API calls from O(n) to O(n/100).
    """
    from .. import gh

    state = load(repo_root)
    state["repo"] = repo

    board_number = config.get("board_number")
    board_owner = config.get("board_owner", "")

    # Fetch all project items once for status lookup
    project_status_map: dict[int, str] = {}
    if board_number and board_owner:
        try:
            items = gh.project_items(board_number, board_owner)
            for item in items:
                num = (item.get("content") or {}).get("number")
                raw_status = item.get("status") or ""
                status = (
                    raw_status
                    if isinstance(raw_status, str)
                    else raw_status.get("name", "")
                )
                if num:
                    project_status_map[int(num)] = status
        except RuntimeError:
            pass

    # Collect all issue numbers for a single batch fetch
    epic_numbers = [e["issue_number"] for e in state["epics"]]
    story_numbers = [
        s["issue_number"] for e in state["epics"] for s in e.get("stories", [])
    ]
    all_numbers = list(
        dict.fromkeys(epic_numbers + story_numbers)
    )  # dedupe, preserve order

    issue_map = gh.issue_states_batch(repo, all_numbers)

    # Apply fetched state back to epics and stories
    for epic in state["epics"]:
        fetched = issue_map.get(epic["issue_number"])
        if fetched:
            epic["status"] = fetched["state"]

        for story in epic.get("stories", []):
            fetched = issue_map.get(story["issue_number"])
            if fetched:
                story["status"] = fetched["state"]
                story["assignee"] = fetched.get("assignee", story.get("assignee", ""))
            story["project_status"] = project_status_map.get(
                story["issue_number"], story.get("project_status", "")
            )

    save(repo_root, state)
    return state
