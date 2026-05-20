"""Tests for whatif_cmd.py — scenario parsing, application, and diff."""

from datetime import date

import pytest

from focal.pm.whatif_cmd import (
    _apply_inject,
    _apply_pto,
    _apply_reestimate,
    _diff_plans,
    _parse_inject,
    _parse_pto,
    _parse_reestimate,
    _working_days_overlap,
)


def _iter(label, start, end, capacity, story_ids=None):
    return {
        "label": label,
        "start": start,
        "end": end,
        "capacity_sp": capacity,
        "story_ids": story_ids or [],
        "notes": [],
    }


def _story(id_, sp, status="open"):
    return {
        "id": id_,
        "sp": sp,
        "status": status,
        "epic_id": "",
        "assignee": "",
        "issue_number": "",
    }


class TestParsePto:
    def test_valid(self):
        result = _parse_pto(["alice:2026-06-02:2026-06-06"])
        assert result[0]["handle"] == "alice"
        assert result[0]["from"] == date(2026, 6, 2)
        assert result[0]["to"] == date(2026, 6, 6)

    def test_at_prefix_stripped(self):
        result = _parse_pto(["@bob:2026-06-02:2026-06-06"])
        assert result[0]["handle"] == "bob"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="HANDLE:FROM:TO"):
            _parse_pto(["no-colons"])


class TestParseInject:
    def test_valid(self):
        result = _parse_inject(["Urgent fix:8"])
        assert result[0]["title"] == "Urgent fix"
        assert result[0]["sp"] == 8

    def test_title_with_colons(self):
        result = _parse_inject(["Fix: the thing:5"])
        assert result[0]["title"] == "Fix: the thing"
        assert result[0]["sp"] == 5

    def test_invalid_sp_raises(self):
        with pytest.raises(ValueError, match="integer"):
            _parse_inject(["Title:notanumber"])


class TestParseReestimate:
    def test_valid(self):
        result = _parse_reestimate(["1.3:13"])
        assert result[0]["story_id"] == "1.3"
        assert result[0]["new_sp"] == 13

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="STORY_ID:SP"):
            _parse_reestimate(["nostoryid"])


class TestWorkingDaysOverlap:
    def test_full_overlap_week(self):
        # Mon-Fri: 5 working days
        days = _working_days_overlap(
            date(2026, 6, 1),
            date(2026, 6, 5),  # Mon-Fri
            "2026-06-01",
            "2026-06-12",
        )
        assert days == 5

    def test_no_overlap(self):
        days = _working_days_overlap(
            date(2026, 6, 1),
            date(2026, 6, 5),
            "2026-06-15",
            "2026-06-26",
        )
        assert days == 0

    def test_empty_iter_dates(self):
        days = _working_days_overlap(date(2026, 6, 1), date(2026, 6, 5), "", "")
        assert days == 0


class TestApplyPto:
    def test_reduces_capacity(self):
        iters = [_iter("I1", "2026-06-01", "2026-06-12", 10)]
        members = [{"handle": "alice", "sp_per_iter": 10}]
        pto = [{"handle": "alice", "from": date(2026, 6, 1), "to": date(2026, 6, 5)}]
        result = _apply_pto(iters, members, pto)
        assert result[0]["capacity_sp"] < 10
        assert result[0]["notes"]

    def test_unknown_handle_ignored(self):
        iters = [_iter("I1", "2026-06-01", "2026-06-12", 10)]
        members = [{"handle": "alice", "sp_per_iter": 10}]
        pto = [{"handle": "bob", "from": date(2026, 6, 1), "to": date(2026, 6, 5)}]
        result = _apply_pto(iters, members, pto)
        assert result[0]["capacity_sp"] == 10

    def test_no_overlap_unchanged(self):
        iters = [_iter("I1", "2026-06-01", "2026-06-12", 10)]
        members = [{"handle": "alice", "sp_per_iter": 10}]
        pto = [{"handle": "alice", "from": date(2026, 7, 1), "to": date(2026, 7, 5)}]
        result = _apply_pto(iters, members, pto)
        assert result[0]["capacity_sp"] == 10


class TestApplyInject:
    def test_prepends_injected_story(self):
        stories = [_story("1.1", 5)]
        result = _apply_inject(stories, [{"title": "P1 fix", "sp": 8}])
        assert result[0]["id"] == "INJ1"
        assert result[0]["sp"] == 8
        assert result[0]["_injected"] is True
        assert result[1]["id"] == "1.1"

    def test_does_not_mutate_input(self):
        stories = [_story("1.1", 5)]
        _apply_inject(stories, [{"title": "X", "sp": 3}])
        assert stories[0]["id"] == "1.1"


class TestApplyReestimate:
    def test_updates_sp(self):
        stories = [_story("1.3", 5)]
        result = _apply_reestimate(stories, [{"story_id": "1.3", "new_sp": 13}])
        assert result[0]["sp"] == 13
        assert result[0]["_reestimated"] is True

    def test_unknown_story_id_ignored(self):
        stories = [_story("1.3", 5)]
        result = _apply_reestimate(stories, [{"story_id": "9.9", "new_sp": 99}])
        assert result[0]["sp"] == 5

    def test_does_not_mutate_input(self):
        stories = [_story("1.3", 5)]
        _apply_reestimate(stories, [{"story_id": "1.3", "new_sp": 13}])
        assert stories[0]["sp"] == 5


class TestDiffPlans:
    def test_no_change(self):
        iters = [_iter("I1", "", "", 10, ["1.1", "1.2"])]
        diffs = _diff_plans(iters, iters)
        assert not diffs[0]["changed"]

    def test_story_slipped(self):
        orig = [_iter("I1", "", "", 10, ["1.1", "1.2"])]
        sim = [_iter("I1", "", "", 5, ["1.1"]), _iter("I2", "", "", 10, ["1.2"])]
        diffs = _diff_plans(orig, sim)
        i1_diff = next(d for d in diffs if d["label"] == "I1")
        assert "1.2" in i1_diff["slipped_out"]

    def test_injection_shows_as_added(self):
        orig = [_iter("I1", "", "", 10, ["1.1"])]
        sim = [_iter("I1", "", "", 10, ["1.1", "INJ1"])]
        diffs = _diff_plans(orig, sim)
        assert "INJ1" in diffs[0]["added_in"]
