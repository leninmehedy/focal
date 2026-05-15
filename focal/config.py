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
    # PM-managed repos: [{"repo": "owner/repo", "repo_root": "/abs/path"}, ...]
    pm_repos: list[dict] = field(default_factory=list)
    state_file: Path = field(
        default_factory=lambda: Path.home() / ".focal" / "state.json"
    )
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
            pm_repos=d.get("pm_repos", []),
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
            "pm_repos": self.pm_repos,
            "state_file": str(self.state_file),
            "log_dir": str(self.log_dir),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        path.chmod(0o600)

    def register_pm_repo(self, repo: str, repo_root: Path) -> bool:
        """Add repo to pm_repos if not already present. Returns True if added."""
        repo_root_str = str(repo_root)
        for entry in self.pm_repos:
            if entry.get("repo") == repo and entry.get("repo_root") == repo_root_str:
                return False
        self.pm_repos.append({"repo": repo, "repo_root": repo_root_str})
        return True
