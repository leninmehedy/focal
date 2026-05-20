"""focal MCP server — exposes Focal PM commands as typed tools for AI agents.

Start with:  focal mcp serve
Wire up with: focal skill install claude  (writes ~/.claude/settings.json)
"""

from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError(
        "MCP support requires the mcp package. Install with: pip install focal[mcp]"
    ) from exc

mcp = FastMCP("focal")

_FOCAL_HOME = Path.home() / ".focal"


def _cfg_dict(config_path: Path) -> dict:
    """Load config as a plain dict, or return empty dict if not found."""
    import dataclasses

    from focal.config import Config

    if not config_path.exists():
        return {}
    return dataclasses.asdict(Config.load(config_path))


# ── Board ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def focal_board_setup(
    owner: str,
    assignee: str,
    repos: list[str],
    create_board: bool = True,
    board_number: int | None = None,
    board_title: str = "My Board",
    done_status: str = "✅ Done",
) -> dict:
    """Set up Focal board sync non-interactively.

    Creates a GitHub Projects board (create_board=True) or uses an existing one
    (create_board=False, board_number required). Writes ~/.focal/config.json.

    Ask the user for owner, assignee, and repos before calling this tool.
    """
    from focal.wizard import run as wizard_run

    result = wizard_run(
        focal_home=_FOCAL_HOME,
        owner=owner,
        assignee=assignee,
        repos=repos,
        create_board=create_board,
        board_number=board_number,
        board_title=board_title,
        done_status=done_status,
    )
    if result is None:
        return {"ok": False, "error": "Setup failed — check output above"}
    return {"ok": True, **result}


@mcp.tool()
def focal_board_sync() -> dict:
    """Trigger a board sync immediately — pulls open assigned issues onto the personal
    board and pushes status changes back to origin projects.

    Useful after creating a batch of new issues to sync them without waiting for
    the next scheduled run.
    """
    from focal._cli import FOCAL_HOME
    from focal.config import Config
    from focal.sync import Syncer, load_status_map

    config_path = FOCAL_HOME / "config.json"
    if not config_path.exists():
        return {"ok": False, "error": "Not configured. Run focal_board_setup first."}
    cfg = Config.load(config_path)
    status_map = load_status_map(FOCAL_HOME / "status_map.json")
    syncer = Syncer(cfg, status_map, config_path=config_path)

    # Capture counters by monkey-patching the log temporarily
    counters: dict = {"added": 0, "inherited": 0, "pushed": 0, "stale": 0}
    original_info = syncer.log.info

    def _capturing_info(msg: str, *args, **kwargs):
        original_info(msg, *args, **kwargs)
        if msg.startswith("Sync complete"):
            for key in counters:
                import re

                m = re.search(rf"{key}: (\d+)", msg)
                if m:
                    counters[key] = int(m.group(1))

    syncer.log.info = _capturing_info
    syncer.run()
    syncer.log.info = original_info
    return {"ok": True, **counters}


# ── PM — repo lifecycle ───────────────────────────────────────────────────────


@mcp.tool()
def focal_pm_init(repo: str, repo_root: str = ".") -> dict:
    """Bootstrap a repo with the Focal PM structure — creates docs/focal/,
    issue templates, and labels. Safe to re-run. Registers the repo for
    focal cache refresh-all.
    """
    from focal.pm import init_cmd

    root = Path(repo_root).resolve()
    init_cmd.run(repo=repo, repo_root=root)
    return {
        "ok": True,
        "repo": repo,
        "repo_root": str(root),
    }


@mcp.tool()
def focal_pm_adopt(
    repo: str,
    repo_root: str = ".",
    epic_labels: str = "epic",
    story_labels: str = "story",
    sp_field: str | None = None,
    default_sp: int | None = None,
    apply: bool = True,
    normalise: bool = False,
) -> dict:
    """Bootstrap the local state cache from existing GitHub issues.

    Use when introducing Focal to a repo that already has epics and stories.
    epic_labels / story_labels: comma-separated GitHub label names.
    apply=False performs a dry-run (no files written).
    """
    from focal.pm import adopt_cmd, pm_state

    root = Path(repo_root).resolve()
    adopt_cmd.run(
        repo=repo,
        repo_root=root,
        epic_labels=[lb.strip() for lb in epic_labels.split(",")],
        story_labels=[lb.strip() for lb in story_labels.split(",")],
        sp_field=sp_field,
        default_sp=default_sp,
        apply=apply,
        normalise=normalise,
        prompt_missing=False,
    )
    state = pm_state.load(root)
    epics = state.get("epics", [])
    stories = [s for e in epics for s in e.get("stories", [])]
    sp_missing = sum(1 for s in stories if not s.get("sp"))
    return {
        "ok": True,
        "epics": len(epics),
        "stories": len(stories),
        "sp_missing": sp_missing,
        "state_path": str(root / "docs" / "focal" / ".cache" / "focal-state.json"),
    }


# ── PM — backlog ──────────────────────────────────────────────────────────────


@mcp.tool()
def focal_pm_epic_create(
    repo: str,
    title: str,
    description: str,
    sp: int,
    repo_root: str = ".",
) -> dict:
    """Create a GitHub epic issue and record it in docs/focal/epics.md."""
    from focal.pm import epic_cmd

    root = Path(repo_root).resolve()
    config_path = _FOCAL_HOME / "config.json"
    config = _cfg_dict(config_path)
    issue_number, node_id = epic_cmd.run(
        repo=repo,
        repo_root=root,
        config=config,
        title=title,
        description=description,
        sp=sp,
    )
    return {
        "ok": True,
        "issue_number": issue_number,
        "url": f"https://github.com/{repo}/issues/{issue_number}",
    }


@mcp.tool()
def focal_pm_story_create(
    repo: str,
    epic_id: str,
    title: str,
    description: str,
    sp: int,
    repo_root: str = ".",
) -> dict:
    """Create a story linked to an existing epic (e.g. epic_id='E1')."""
    from focal.pm import story_cmd

    root = Path(repo_root).resolve()
    config_path = _FOCAL_HOME / "config.json"
    config = _cfg_dict(config_path)
    from focal.pm import pm_state

    state_before = pm_state.load(root)
    ids_before = {s["id"] for e in state_before.get("epics", []) for s in e.get("stories", [])}

    story_cmd.run(
        repo=repo,
        repo_root=root,
        config=config,
        epic_id=epic_id,
        title=title,
        description=description,
        sp=sp,
    )

    state_after = pm_state.load(root)
    new_stories = [
        s
        for e in state_after.get("epics", [])
        for s in e.get("stories", [])
        if s["id"] not in ids_before
    ]
    if new_stories:
        s = new_stories[0]
        return {
            "ok": True,
            "issue_number": s.get("issue_number"),
            "story_id": s["id"],
            "url": s.get("issue_url", f"https://github.com/{repo}/issues/{s.get('issue_number', '')}"),
        }
    return {"ok": False, "error": "Story creation failed — check output above"}


# ── PM — planning ─────────────────────────────────────────────────────────────


@mcp.tool()
def focal_pm_plan(
    repo: str,
    weeks: int,
    start: str,
    team: str,
    pto: list[str] | None = None,
    goals: str | None = None,
    repo_root: str = ".",
) -> dict:
    """Generate docs/focal/iteration-planning.md from the local state cache.

    team: comma-separated handle:sp_per_iter pairs, e.g. "alice:8,bob:6"
    pto:  list of "handle:YYYY-MM-DD:YYYY-MM-DD" strings
    goals: comma-separated "LABEL:goal text" pairs, e.g. "I1:Ship auth,I2:Close E2"
    """
    from focal.pm import plan_cmd

    root = Path(repo_root).resolve()
    config_path = _FOCAL_HOME / "config.json"
    config = _cfg_dict(config_path)
    goals_dict: dict | None = None
    if goals:
        goals_dict = {}
        for part in goals.split(","):
            if ":" in part:
                label, goal_text = part.split(":", 1)
                goals_dict[label.strip()] = goal_text.strip()

    plan_cmd.run(
        repo=repo,
        repo_root=root,
        config=config,
        weeks=weeks,
        start_date=start,
        team=team,
        pto=pto or None,
        goals=goals_dict,
        refresh=False,
    )
    from focal.pm import iteration_parser

    plan_path = root / "docs" / "focal" / "iteration-planning.md"
    plan = iteration_parser.load(plan_path)
    iterations = plan.get("iterations", []) if plan else []
    total_sp = sum(it.get("capacity_sp", 0) for it in iterations)
    return {
        "ok": True,
        "iterations": len(iterations),
        "total_capacity_sp": total_sp,
    }


@mcp.tool()
def focal_pm_whatif(
    repo: str,
    pto: list[str] | None = None,
    inject: list[str] | None = None,
    reestimate: list[str] | None = None,
    repo_root: str = ".",
) -> dict:
    """Simulate the iteration plan under hypothetical scenarios. Dry-run only —
    never modifies files.

    pto:        list of "handle:YYYY-MM-DD:YYYY-MM-DD"
    inject:     list of "Title:SP"
    reestimate: list of "STORY_ID:SP"

    Returns per-iteration diffs with slipped and added stories.
    """
    import copy

    from focal.pm import pm_state
    from focal.pm.iteration_parser import load as load_plan
    from focal.pm.plan_helpers import assign_stories_to_iters
    from focal.pm.whatif_cmd import (
        _apply_inject,
        _apply_pto,
        _apply_reestimate,
        _diff_plans,
        _parse_inject,
        _parse_pto,
        _parse_reestimate,
    )

    root = Path(repo_root).resolve()
    plan_path = root / "docs" / "focal" / "iteration-planning.md"
    plan = load_plan(plan_path)
    if plan is None:
        return {"ok": False, "error": "No iteration plan found. Run focal_pm_plan first."}

    state = pm_state.load(root)
    all_stories: list[dict] = []
    for epic in state.get("epics", []):
        for s in epic.get("stories", []):
            all_stories.append({**s, "epic_id": epic.get("id", "")})

    if not all_stories:
        return {"ok": False, "error": "No stories in cache. Run focal_cache_refresh first."}

    try:
        pto_list = _parse_pto(pto or [])
        inject_list = _parse_inject(inject or [])
        reestimate_list = _parse_reestimate(reestimate or [])
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    original_iters = plan["iterations"]
    members = plan["members"]
    sim_iters = copy.deepcopy(original_iters)
    sim_stories = copy.deepcopy(all_stories)

    if pto_list:
        sim_iters = _apply_pto(sim_iters, members, pto_list)
    if inject_list:
        sim_stories = _apply_inject(sim_stories, inject_list)
    if reestimate_list:
        sim_stories = _apply_reestimate(sim_stories, reestimate_list)

    sim_iters = assign_stories_to_iters(sim_stories, sim_iters)
    orig_iters_assigned = assign_stories_to_iters(all_stories, original_iters)
    diffs = _diff_plans(orig_iters_assigned, sim_iters)

    capacity_notes = [
        {"iteration": it["label"], "notes": it.get("notes", [])}
        for it in sim_iters
        if it.get("notes")
    ]
    total_slipped = sum(len(d["slipped_out"]) for d in diffs)
    total_added = sum(len(d["added_in"]) for d in diffs)

    return {
        "ok": True,
        "diffs": [
            {
                "iteration": d["label"],
                "changed": d["changed"],
                "slipped_out": d["slipped_out"],
                "added_in": d["added_in"],
                "orig_story_count": d["orig_count"],
                "sim_story_count": d["sim_count"],
            }
            for d in diffs
        ],
        "capacity_notes": capacity_notes,
        "summary": {
            "total_slipped": total_slipped,
            "total_added": total_added,
            "changed_iterations": sum(1 for d in diffs if d["changed"]),
        },
    }


@mcp.tool()
def focal_pm_status(repo: str, repo_root: str = ".", refresh: bool = False) -> dict:
    """Return the current iteration status as structured data."""
    from focal.pm import pm_state
    from focal.pm.status_cmd import _current_iteration, _days_remaining

    root = Path(repo_root).resolve()
    config_path = _FOCAL_HOME / "config.json"
    config = _cfg_dict(config_path)
    state = pm_state.load(root)
    if refresh:
        state = pm_state.refresh_from_github(root, repo, config)

    current_iter = _current_iteration(state)
    if not current_iter:
        return {"ok": False, "error": "No active iteration found."}

    all_stories = pm_state.all_stories(state)
    story_map = {s["id"]: s for s in all_stories}
    planned = [story_map[sid] for sid in current_iter.get("story_ids", []) if sid in story_map]

    delivered, in_progress, blocked, not_started = [], [], [], []
    for s in planned:
        ps = s.get("project_status", "").lower()
        if s.get("status") == "closed":
            delivered.append(s)
        elif "blocked" in ps or "✋" in ps:
            blocked.append(s)
        elif "progress" in ps or "review" in ps:
            in_progress.append(s)
        else:
            not_started.append(s)

    return {
        "ok": True,
        "iteration": current_iter["label"],
        "start": current_iter.get("start", ""),
        "end": current_iter.get("end", ""),
        "capacity_sp": current_iter.get("capacity_sp", 0),
        "delivered_sp": sum(s.get("sp", 0) for s in delivered),
        "in_progress_sp": sum(s.get("sp", 0) for s in in_progress),
        "blocked_count": len(blocked),
        "not_started_count": len(not_started),
        "days_remaining": _days_remaining(current_iter),
        "carry_over": [
            {"id": s["id"], "title": s.get("title", ""), "sp": s.get("sp", 0)}
            for s in not_started + blocked
        ],
    }


# ── PM — delivery close ───────────────────────────────────────────────────────


@mcp.tool()
def focal_pm_retro(
    repo: str,
    iteration_label: str,
    goal_met: bool,
    slip_reasons: list[str] | None = None,
    went_well: list[str] | None = None,
    to_improve: list[str] | None = None,
    action_items: list[str] | None = None,
    notes: str = "",
    repo_root: str = ".",
) -> dict:
    """Log a completed iteration to docs/focal/retro-log.md.

    slip_reasons: list of "STORY_ID:CODE" or "STORY_ID:CODE:note"
                  Codes: SCOPE BLOCKED LEAVE TRAVEL CARRY REPRIORITY
    action_items: list of "handle:action text:YYYY-MM-DD" (due date optional)

    Collect carry-over stories via focal_pm_status first so you can ask the user
    for slip reasons before calling this tool.
    """
    from focal.pm import retro_cmd

    root = Path(repo_root).resolve()
    config_path = _FOCAL_HOME / "config.json"
    config = _cfg_dict(config_path)

    parsed_actions = []
    for a in action_items or []:
        parts = a.split(":", 2)
        if len(parts) >= 2:
            parsed_actions.append(
                {
                    "handle": parts[0].strip().lstrip("@"),
                    "action": parts[1].strip(),
                    "due": parts[2].strip() if len(parts) == 3 else "",
                }
            )

    retro_cmd.run(
        repo=repo,
        repo_root=root,
        config=config,
        iteration_label=iteration_label,
        goal_met=goal_met,
        slip_reasons=slip_reasons,
        went_well=went_well or [],
        to_improve=to_improve or [],
        action_items=parsed_actions,
        notes=notes,
    )
    return {"ok": True, "iteration": iteration_label}


# ── PM — design docs ──────────────────────────────────────────────────────────


@mcp.tool()
def focal_pm_design_list(repo_root: str = ".") -> dict:
    """List all design docs in docs/focal/design/ with their status and linked epic."""
    import re

    root = Path(repo_root).resolve()
    design_dir = root / "docs" / "focal" / "design"
    if not design_dir.exists():
        return {"ok": False, "error": "docs/focal/design/ not found. Run focal_pm_init first."}

    designs = []
    for path in sorted(design_dir.glob("D*.md")):
        text = path.read_text(encoding="utf-8")
        fm: dict = {}
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip()
        designs.append(
            {
                "id": fm.get("id", path.stem),
                "title": fm.get("title", ""),
                "status": fm.get("status", ""),
                "epic": fm.get("epic", ""),
                "updated": fm.get("updated", ""),
                "file": path.name,
            }
        )
    return {"ok": True, "designs": designs}


# ── Cache ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def focal_cache_refresh(repo: str, repo_root: str = ".") -> dict:
    """Re-fetch one repo's epics and stories from GitHub into the local cache."""
    from focal.pm import pm_state, sync_state_cmd

    root = Path(repo_root).resolve()
    config_path = _FOCAL_HOME / "config.json"
    config = _cfg_dict(config_path)
    sync_state_cmd.run(repo=repo, repo_root=root, config=config)
    state = pm_state.load(root)
    epics = state.get("epics", [])
    stories = [s for e in epics for s in e.get("stories", [])]
    return {
        "ok": True,
        "epics": len(epics),
        "stories": len(stories),
        "last_synced": state.get("last_synced", ""),
    }


@mcp.tool()
def focal_cache_status() -> dict:
    """Show sync health across all registered PM repos."""
    import json

    from focal._cli import FOCAL_HOME

    config_path = FOCAL_HOME / "config.json"
    if not config_path.exists():
        return {"ok": False, "error": "Not configured. Run focal_board_setup first."}

    with open(config_path) as f:
        cfg_data = json.load(f)

    pm_repos = cfg_data.get("pm_repos", [])
    result = []
    for entry in pm_repos:
        repo = entry if isinstance(entry, str) else entry.get("repo", "")
        repo_root = (
            Path(entry["repo_root"]) if isinstance(entry, dict) and "repo_root" in entry
            else Path(".")
        )
        state_path = repo_root / "docs" / "focal" / ".cache" / "focal-state.json"
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
            epics = state.get("epics", [])
            stories = [s for e in epics for s in e.get("stories", [])]
            result.append(
                {
                    "repo": repo,
                    "epics": len(epics),
                    "stories": len(stories),
                    "last_synced": state.get("last_synced", "never"),
                    "status": "ok",
                }
            )
        else:
            result.append(
                {"repo": repo, "epics": 0, "stories": 0, "last_synced": "never", "status": "no cache"}
            )
    return {"ok": True, "repos": result}


# ── Server entry point ────────────────────────────────────────────────────────


def serve() -> None:
    mcp.run(transport="stdio")
