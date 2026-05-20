"""Tests for mcp_server.py tool return shapes and helper logic.

These tests verify tool function structure without calling GitHub or writing files.
MCP tools return dicts; we test the shape and error paths.
"""

import json
import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── _cfg_dict ─────────────────────────────────────────────────────────────────


def test_cfg_dict_missing_file(tmp_path):
    from focal.mcp_server import _cfg_dict

    result = _cfg_dict(tmp_path / "nonexistent.json")
    assert result == {}


def test_cfg_dict_loads_config(tmp_path):
    from focal.config import Config
    from focal.mcp_server import _cfg_dict

    cfg = Config(
        board_owner="testowner",
        board_number=1,
        assignee="testuser",
        repos=["org/repo"],
        done_status="✅ Done",
        status_field_id="FIELD_ID",
    )
    p = tmp_path / "config.json"
    cfg.save(p)

    result = _cfg_dict(p)
    assert result["board_owner"] == "testowner"
    assert result["assignee"] == "testuser"
    assert result["repos"] == ["org/repo"]


# ── focal_board_sync error path ───────────────────────────────────────────────


def test_focal_board_sync_not_configured(tmp_path, monkeypatch):
    import focal._cli as cli_module
    monkeypatch.setattr(cli_module, "FOCAL_HOME", tmp_path)

    from focal.mcp_server import focal_board_sync

    result = focal_board_sync()
    assert result["ok"] is False
    assert "Not configured" in result["error"]


# ── focal_pm_status error path ────────────────────────────────────────────────


def test_focal_pm_status_no_iteration(tmp_path):
    from focal.mcp_server import focal_pm_status
    from focal.pm import pm_state

    state = {"epics": [], "iterations": []}
    pm_state.save(tmp_path, state)

    with patch("focal.mcp_server._FOCAL_HOME", tmp_path):
        # No config.json needed for this path since state has no iterations
        result = focal_pm_status(repo="org/repo", repo_root=str(tmp_path))
    assert result["ok"] is False
    assert "No active iteration" in result["error"]


def test_focal_pm_status_returns_shape(tmp_path):
    """focal_pm_status returns expected keys when an active iteration exists."""
    import datetime
    from focal.mcp_server import focal_pm_status
    from focal.pm import pm_state

    today = datetime.date.today()
    start = (today - datetime.timedelta(days=3)).isoformat()
    end = (today + datetime.timedelta(days=4)).isoformat()
    state = {
        "epics": [
            {
                "id": "E1",
                "title": "Epic 1",
                "stories": [
                    {
                        "id": "1.1",
                        "title": "Story A",
                        "sp": 3,
                        "status": "closed",
                        "project_status": "Done",
                    }
                ],
            }
        ],
        "iterations": [
            {
                "label": "I1",
                "start": start,
                "end": end,
                "capacity_sp": 8,
                "story_ids": ["1.1"],
            }
        ],
    }
    pm_state.save(tmp_path, state)

    with patch("focal.mcp_server._FOCAL_HOME", tmp_path):
        result = focal_pm_status(repo="org/repo", repo_root=str(tmp_path))

    assert result["ok"] is True
    assert result["iteration"] == "I1"
    assert result["delivered_sp"] == 3
    assert "days_remaining" in result
    assert "carry_over" in result


# ── focal_pm_design_list ──────────────────────────────────────────────────────


def test_focal_pm_design_list_no_dir(tmp_path):
    from focal.mcp_server import focal_pm_design_list

    result = focal_pm_design_list(repo_root=str(tmp_path))
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_focal_pm_design_list_parses_frontmatter(tmp_path):
    from focal.mcp_server import focal_pm_design_list

    design_dir = tmp_path / "docs" / "focal" / "design"
    design_dir.mkdir(parents=True)
    (design_dir / "D001-test.md").write_text(
        "---\nid: D001\ntitle: Test Design\nstatus: Draft\nepic: E1\nupdated: 2026-01-01\n---\n\n# Body\n"
    )

    result = focal_pm_design_list(repo_root=str(tmp_path))
    assert result["ok"] is True
    assert len(result["designs"]) == 1
    d = result["designs"][0]
    assert d["id"] == "D001"
    assert d["status"] == "Draft"
    assert d["epic"] == "E1"


# ── focal_cache_status ────────────────────────────────────────────────────────


def test_focal_cache_status_not_configured(tmp_path):
    from focal.mcp_server import focal_cache_status

    with patch("focal._cli.FOCAL_HOME", tmp_path):
        result = focal_cache_status()
    assert result["ok"] is False
    assert "Not configured" in result["error"]


def test_focal_cache_status_returns_repos(tmp_path):
    from focal.mcp_server import focal_cache_status

    cfg = {"owner": "x", "assignee": "x", "repos": [], "pm_repos": []}
    (tmp_path / "config.json").write_text(json.dumps(cfg))

    with patch("focal._cli.FOCAL_HOME", tmp_path):
        result = focal_cache_status()
    assert result["ok"] is True
    assert result["repos"] == []


# ── focal_pm_whatif error path ────────────────────────────────────────────────


def test_focal_pm_whatif_no_plan(tmp_path):
    from focal.mcp_server import focal_pm_whatif

    result = focal_pm_whatif(repo="org/repo", repo_root=str(tmp_path))
    assert result["ok"] is False
    assert "No iteration plan" in result["error"]
