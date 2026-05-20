"""Tests for breakdown_parser.parse()."""

import textwrap
from pathlib import Path

import pytest

from focal.pm.breakdown_parser import parse


@pytest.fixture()
def tmp_doc(tmp_path):
    def _make(content: str) -> Path:
        p = tmp_path / "D001-test.md"
        p.write_text(textwrap.dedent(content))
        return p

    return _make


class TestParse:
    def test_full_breakdown(self, tmp_doc):
        doc = tmp_doc("""
            ---
            id: D001
            status: Planned
            ---

            ## Breakdown hint

            Epic: Build the widget (~13 SP)
              - Story: Add widget model (3 SP)
              - Story: Add widget API (5 SP)
              - Story: Add widget UI (5 SP)
        """)
        result = parse(doc)
        assert result is not None
        assert result["epic_title"] == "Build the widget"
        assert result["epic_sp"] == 13
        assert len(result["stories"]) == 3
        assert result["stories"][0] == {"title": "Add widget model", "sp": 3}
        assert result["stories"][2] == {"title": "Add widget UI", "sp": 5}

    def test_no_breakdown_section_returns_none(self, tmp_doc):
        doc = tmp_doc("""
            ---
            id: D001
            ---

            ## Abstract

            No breakdown here.
        """)
        assert parse(doc) is None

    def test_breakdown_section_no_epic_returns_none(self, tmp_doc):
        doc = tmp_doc("""
            ---
            id: D001
            ---

            ## Breakdown hint

              - Story: Some story (2 SP)
        """)
        assert parse(doc) is None

    def test_epic_without_tilde(self, tmp_doc):
        doc = tmp_doc("""
            ## Breakdown hint

            Epic: Plain epic (8 SP)
              - Story: A story (8 SP)
        """)
        result = parse(doc)
        assert result["epic_sp"] == 8

    def test_stories_empty(self, tmp_doc):
        doc = tmp_doc("""
            ## Breakdown hint

            Epic: Solo epic (~5 SP)
        """)
        result = parse(doc)
        assert result["epic_title"] == "Solo epic"
        assert result["stories"] == []

    def test_stops_at_next_section(self, tmp_doc):
        doc = tmp_doc("""
            ## Breakdown hint

            Epic: My epic (~3 SP)
              - Story: Story one (3 SP)

            ## References

            Epic: Fake epic (~99 SP)
              - Story: Should not appear (1 SP)
        """)
        result = parse(doc)
        assert len(result["stories"]) == 1
        assert result["epic_sp"] == 3

    def test_case_insensitive_keywords(self, tmp_doc):
        doc = tmp_doc("""
            ## Breakdown hint

            EPIC: Upper case (~2 SP)
              - STORY: Upper story (2 SP)
        """)
        result = parse(doc)
        assert result["epic_title"] == "Upper case"
        assert result["stories"][0]["title"] == "Upper story"

    def test_real_d002_breakdown(self, tmp_doc):
        doc = tmp_doc("""
            ## Breakdown hint

            Epic: Adopt existing project into Focal PM management (`focal pm adopt`) (~34 SP)
              - Story: Document Focal issue format standard — label, title, body table, sub-issue rules (2 SP)
              - Story: Extend gh.py — issues_by_label(), issue_sub_issues(), project_field_value() (3 SP)
              - Story: Implement sp_extractor.py — extract SP from title, body table, project field (5 SP)
        """)
        result = parse(doc)
        assert result["epic_sp"] == 34
        assert len(result["stories"]) == 3
        assert result["stories"][1]["sp"] == 3
