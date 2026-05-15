import json
from pathlib import Path

# url -> {personal_status, origin_status}
State = dict[str, dict[str, str]]


def load(path: Path) -> State:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save(state: State, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
