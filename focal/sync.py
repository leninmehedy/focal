import json
import re
from pathlib import Path
from typing import Optional

from . import gh, log, notify
from . import state as state_mod
from .config import Config


def normalize(s: str) -> str:
    """Strip leading emoji and whitespace for fuzzy status matching."""
    return re.sub(r"^[\U00010000-\U0010ffff\s\-]+", "", s).strip()


def load_status_map(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


class Syncer:
    def __init__(self, cfg: Config, status_map: dict):
        self.cfg = cfg
        self.status_map = status_map
        self.log = log.get()

        self.project_id = gh.project_id(cfg.board_number, cfg.board_owner)
        self.log.info(f"Board: #{cfg.board_number} ({self.project_id})")

        fields = gh.project_fields(cfg.board_number, cfg.board_owner)
        self.personal_options: list[dict] = next(
            (f.get("options", []) for f in fields if f.get("name") == "Status"), []
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _personal_option_id(self, status_name: str) -> Optional[str]:
        target = normalize(status_name)
        return next(
            (o["id"] for o in self.personal_options if normalize(o["name"]) == target),
            None,
        )

    def _translate(self, project_id: str, origin_status: str) -> Optional[str]:
        mapped = self.status_map.get(project_id, {}).get(origin_status, origin_status)
        target = normalize(mapped)
        return next(
            (
                o["name"]
                for o in self.personal_options
                if normalize(o["name"]) == target
            ),
            None,
        )

    def _set_personal_status(self, item_id: str, status_name: str) -> None:
        option_id = self._personal_option_id(status_name)
        if not option_id:
            self.log.warning(f"No personal board option for '{status_name}' — skipping")
            return
        gh.set_item_field(self.project_id, item_id, self.cfg.status_field_id, option_id)

    def _push_to_origin(self, origin_item: dict, status_name: str) -> None:
        field = gh.origin_status_field(origin_item["projectId"])
        if not field:
            self.log.warning(
                f"Could not fetch Status field for '{origin_item['projectTitle']}'"
            )
            return
        target = normalize(status_name)
        option_id = next(
            (
                o["id"]
                for o in field.get("options", [])
                if normalize(o["name"]) == target
            ),
            None,
        )
        if not option_id:
            self.log.warning(
                f"'{status_name}' not found in '{origin_item['projectTitle']}' — skipping"
            )
            return
        gh.set_item_field(
            origin_item["projectId"], origin_item["itemId"], field["id"], option_id
        )
        self.log.info(f"  ✔ Pushed '{status_name}' → '{origin_item['projectTitle']}'")

    # ── Main sync ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        cfg = self.cfg
        added = pushed = stale = inherited = 0

        # Load state and extract last_synced
        state = state_mod.load(cfg.state_file)
        last_synced: Optional[str] = state.get("last_synced")
        issues = state["issues"]
        is_incremental = last_synced is not None

        # Step 1: Add open assigned issues to personal board
        self.log.info("=== Step 1: Adding open assigned issues ===")
        open_urls: set[str] = set()
        for repo in cfg.repos:
            self.log.info(f"Checking {repo} ...")
            if is_incremental:
                self.log.info(f"  Incremental sync since {last_synced}")
            else:
                self.log.info("  Full sync (first run)")
            try:
                urls = gh.open_assigned_issues(
                    repo, cfg.assignee, since=last_synced if is_incremental else None
                )
            except RuntimeError as e:
                self.log.warning(f"  Could not list issues: {e}")
                continue
            if not urls:
                self.log.info("  No open assigned issues")
                continue
            for url in urls:
                open_urls.add(url)
                self.log.info(f"Adding: {url}")
                try:
                    gh.add_item(cfg.board_number, cfg.board_owner, url)
                    added += 1
                except RuntimeError as e:
                    self.log.warning(f"  item-add failed: {e}")

        # Fetch current board state
        self.log.info("=== Fetching personal board state ===")
        board_items = gh.project_items(cfg.board_number, cfg.board_owner)

        # Step 1b: Extend open_urls to cover repos on the board but not in cfg.repos.
        # Without this, issues from unwatched repos are incorrectly marked Done.
        watched = set(cfg.repos)
        board_repos: set[str] = set()
        for item in board_items:
            url = item.get("content", {}).get("url", "")
            # URL shape: https://github.com/owner/repo/issues/N
            parts = url.split("/")
            if len(parts) >= 5 and parts[2] == "github.com":
                board_repos.add(f"{parts[3]}/{parts[4]}")
        extra_repos = board_repos - watched
        if extra_repos:
            self.log.info(
                f"=== Step 1b: Checking {len(extra_repos)} board repo(s) not in cfg.repos ==="
            )
            for repo in sorted(extra_repos):
                self.log.info(f"Checking (board-only) {repo} ...")
                try:
                    urls = gh.open_assigned_issues(repo, cfg.assignee)
                except RuntimeError as e:
                    self.log.warning(f"  Could not list issues: {e}")
                    continue
                for url in urls:
                    open_urls.add(url)

        # Step 2: Detect changes, act
        self.log.info("=== Step 2: Detecting status changes ===")
        new_issues = dict(issues)

        for item in board_items:
            if item.get("content", {}).get("type") != "Issue":
                continue
            url = item.get("content", {}).get("url", "")
            if not url:
                continue

            item_id = item["id"]
            cur = item.get("status") or ""
            prev = issues.get(url, {})
            prev_personal = prev.get("personal_status", "")
            is_new = url not in issues

            if url not in open_urls:
                # Closed or unassigned — move to Done
                if cur != cfg.done_status:
                    self.log.info(f"Stale (closed/unassigned): {url}")
                    self._set_personal_status(item_id, cfg.done_status)
                    stale += 1
                new_issues[url] = {**prev, "personal_status": cfg.done_status}

            elif is_new:
                # New item — inherit status from origin
                self.log.info(f"New item, inheriting origin status: {url}")
                origin_items = gh.issue_project_items(url)
                origin_status = ""
                origin_project_id = ""
                for oi in origin_items:
                    if oi["status"] and not origin_status:
                        origin_status = oi["status"]
                        origin_project_id = oi["projectId"]

                if origin_status:
                    personal = (
                        self._translate(origin_project_id, origin_status)
                        or origin_status
                    )
                    self.log.info(
                        f"  Inherited '{personal}' (origin: '{origin_status}')"
                    )
                    self._set_personal_status(item_id, personal)
                    new_issues[url] = {
                        "personal_status": personal,
                        "origin_status": personal,
                    }
                else:
                    self.log.info("  No origin project status — setting 🆕 New")
                    self._set_personal_status(item_id, "🆕 New")
                    new_issues[url] = {"personal_status": "🆕 New", "origin_status": ""}
                inherited += 1

            elif prev_personal and cur != prev_personal:
                # Personal board moved — push to origin
                self.log.info(f"Pushing '{cur}' to origin: {url}")
                for oi in gh.issue_project_items(url):
                    self._push_to_origin(oi, cur)
                new_issues[url] = {**prev, "personal_status": cur, "origin_status": cur}
                pushed += 1

            else:
                new_issues[url] = {**prev, "personal_status": cur}

        state["issues"] = new_issues
        state_mod.save(state, cfg.state_file)
        sync_mode = "incremental" if is_incremental else "full"
        self.log.info(
            f"Sync complete — added: {added}  inherited: {inherited}  "
            f"pushed: {pushed}  stale: {stale}  ({sync_mode})  log: {cfg.log_dir}"
        )
        if cfg.notifications:
            notify.notify(
                "Focal sync complete",
                f"added: {added}  inherited: {inherited}  pushed: {pushed}  stale: {stale}",
            )
