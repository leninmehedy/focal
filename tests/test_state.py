"""Tests for state.py — load/save and legacy migration."""

import json

from focal.state import load, save


def test_load_missing_file(tmp_path):
    state = load(tmp_path / "state.json")
    assert state == {"last_synced": None, "issues": {}}


def test_load_new_format(tmp_path):
    path = tmp_path / "state.json"
    data = {
        "last_synced": "2026-05-01T10:00:00+00:00",
        "issues": {"https://github.com/o/r/issues/1": {"personal_status": "🆕 New"}},
    }
    path.write_text(json.dumps(data))
    state = load(path)
    assert state["last_synced"] == "2026-05-01T10:00:00+00:00"
    assert "https://github.com/o/r/issues/1" in state["issues"]


def test_load_legacy_format_migrates(tmp_path):
    path = tmp_path / "state.json"
    # old format: bare dict of url → status string
    legacy = {"https://github.com/o/r/issues/1": "🏗 In progress"}
    path.write_text(json.dumps(legacy))
    state = load(path)
    assert state["last_synced"] is None
    assert state["issues"] == legacy


def test_save_stamps_last_synced(tmp_path):
    path = tmp_path / "state.json"
    state = {"last_synced": None, "issues": {}}
    save(state, path)
    saved = json.loads(path.read_text())
    assert saved["last_synced"] is not None
    assert saved["last_synced"].startswith("20")  # ISO timestamp


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "state.json"
    save({"last_synced": None, "issues": {}}, path)
    assert path.exists()


def test_save_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    issues = {"https://github.com/o/r/issues/42": {"personal_status": "✅ Done"}}
    save({"last_synced": None, "issues": issues}, path)
    reloaded = load(path)
    assert reloaded["issues"] == issues
    assert reloaded["last_synced"] is not None
