import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    board_owner: str
    board_number: int
    assignee: str
    status_field_id: str
    done_status: str
    repos: list[str]
    state_file: Path = field(default_factory=lambda: Path.home() / ".focal" / "state.json")
    log_dir: Path = field(default_factory=lambda: Path.home() / ".focal" / "logs")

    @classmethod
    def load(cls, path: Path) -> "Config":
        with open(path) as f:
            d = json.load(f)
        return cls(
            board_owner=d["board_owner"],
            board_number=int(d["board_number"]),
            assignee=d["assignee"],
            status_field_id=d["status_field_id"],
            done_status=d["done_status"],
            repos=d["repos"],
            state_file=Path(d.get("state_file", "~/.focal/state.json")).expanduser(),
            log_dir=Path(d.get("log_dir", "~/.focal/logs")).expanduser(),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "board_owner": self.board_owner,
            "board_number": self.board_number,
            "assignee": self.assignee,
            "status_field_id": self.status_field_id,
            "done_status": self.done_status,
            "repos": self.repos,
            "state_file": str(self.state_file),
            "log_dir": str(self.log_dir),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        path.chmod(0o600)
