"""Tests for velocity_cmd._parse_retro_log()."""

from pathlib import Path

from focal.pm.velocity_cmd import _parse_retro_log

RETRO_LOG_SINGLE = """\
# Retro Log

## I1 — May 5–16 2026

| **Metric** | **Value** |
|---|---|
| **Capacity** | 16 SP |
| **Planned** | 14 SP |
| **Delivered** | 12 SP |
| **Carry-over** | 2 SP |
| **Goal met** | Yes |
"""

RETRO_LOG_MULTI = """\
# Retro Log

## I1 — May 5–16 2026

| **Metric** | **Value** |
|---|---|
| **Capacity** | 16 SP |
| **Planned** | 14 SP |
| **Delivered** | 12 SP |
| **Carry-over** | 2 SP |
| **Goal met** | Yes |

## I2 — May 19–30 2026

| **Metric** | **Value** |
|---|---|
| **Capacity** | 16 SP |
| **Planned** | 16 SP |
| **Delivered** | 10 SP |
| **Carry-over** | 6 SP |
| **Goal met** | No |
"""

RETRO_LOG_EMPTY = "# Retro Log\n\nNo iterations yet.\n"


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "retro-log.md"
    p.write_text(content)
    return p


def test_parse_single_iteration(tmp_path):
    rows = _parse_retro_log(_write(tmp_path, RETRO_LOG_SINGLE))
    assert len(rows) == 1
    r = rows[0]
    assert r["label"] == "I1"
    assert r["capacity_sp"] == 16
    assert r["planned_sp"] == 14
    assert r["delivered_sp"] == 12
    assert r["carry_sp"] == 2
    assert r["goal_met"] is True


def test_parse_multiple_iterations(tmp_path):
    rows = _parse_retro_log(_write(tmp_path, RETRO_LOG_MULTI))
    assert len(rows) == 2
    assert rows[0]["label"] == "I1"
    assert rows[1]["label"] == "I2"
    assert rows[1]["goal_met"] is False
    assert rows[1]["delivered_sp"] == 10
    assert rows[1]["carry_sp"] == 6


def test_parse_empty_log(tmp_path):
    rows = _parse_retro_log(_write(tmp_path, RETRO_LOG_EMPTY))
    assert rows == []


def test_goal_met_case_insensitive(tmp_path):
    content = RETRO_LOG_SINGLE.replace(
        "| **Goal met** | Yes |", "| **Goal met** | YES |"
    )
    rows = _parse_retro_log(_write(tmp_path, content))
    assert rows[0]["goal_met"] is True


def test_goal_not_met(tmp_path):
    content = RETRO_LOG_SINGLE.replace(
        "| **Goal met** | Yes |", "| **Goal met** | No |"
    )
    rows = _parse_retro_log(_write(tmp_path, content))
    assert rows[0]["goal_met"] is False


def test_missing_sp_defaults_to_zero(tmp_path):
    content = RETRO_LOG_SINGLE.replace(
        "| **Delivered** | 12 SP |", "| **Delivered** | — |"
    )
    rows = _parse_retro_log(_write(tmp_path, content))
    assert rows[0]["delivered_sp"] == 0
