import json
from datetime import datetime, timezone
from pathlib import Path

# New on-disk format:
# {"last_synced": "2026-05-16T10:00:00+00:00", "issues": {url: {personal_status, origin_status}}}
# Old format (bare dict of url->status) is still accepted for backward compat.
State = dict  # {"last_synced": str | None, "issues": dict[str, dict[str, str]]}


def load(path: Path) -> State:
    if not path.exists():
        return {"last_synced": None, "issues": {}}
    with open(path) as f:
        data = json.load(f)
    if "issues" not in data:
        # old format — migrate in-memory
        return {"last_synced": None, "issues": data}
    return data


def save(state: State, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["last_synced"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
