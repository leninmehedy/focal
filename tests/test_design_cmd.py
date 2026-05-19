"""Tests for design_cmd.py — frontmatter parsing, load_designs, summary_lines."""

from pathlib import Path

import pytest

from focal.pm.design_cmd import _parse_frontmatter, load_designs, summary_lines


def _write_doc(tmp_path: Path, filename: str, frontmatter: dict, body: str = "") -> Path:
    lines = ["---"]
    for k, v in frontmatter.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    p = tmp_path / filename
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


class TestParseFrontmatter:
    def test_basic_fields(self, tmp_path):
        p = _write_doc(
            tmp_path,
            "D001.md",
            {"id": "D001", "title": "My Feature", "status": "Draft"},
        )
        fm = _parse_frontmatter(p)
        assert fm["id"] == "D001"
        assert fm["title"] == "My Feature"
        assert fm["status"] == "Draft"

    def test_strips_inline_comments(self, tmp_path):
        p = tmp_path / "D001.md"
        p.write_text(
            "---\nstatus: Draft     # Draft | Planned | Active\n---\n", encoding="utf-8"
        )
        fm = _parse_frontmatter(p)
        assert fm["status"] == "Draft"

    def test_no_frontmatter_returns_empty(self, tmp_path):
        p = tmp_path / "no_fm.md"
        p.write_text("# Just a heading\n\nSome text.", encoding="utf-8")
        assert _parse_frontmatter(p) == {}

    def test_unclosed_frontmatter_returns_empty(self, tmp_path):
        p = tmp_path / "bad.md"
        p.write_text("---\nid: D001\ntitle: Oops\n", encoding="utf-8")
        assert _parse_frontmatter(p) == {}


class TestLoadDesigns:
    def test_loads_docs_sorted_by_status_then_id(self, tmp_path):
        _write_doc(tmp_path, "D002.md", {"id": "D002", "title": "B", "status": "Active", "epic": "10", "created": "2026-01-01", "updated": "2026-01-01"})
        _write_doc(tmp_path, "D001.md", {"id": "D001", "title": "A", "status": "Planned", "epic": "5", "created": "2026-01-01", "updated": "2026-01-01"})
        docs = load_designs(tmp_path)
        # Planned (index 1) comes before Active (index 2) in STATUS_ORDER
        assert docs[0]["id"] == "D001"
        assert docs[1]["id"] == "D002"

    def test_skips_files_without_frontmatter(self, tmp_path):
        (tmp_path / "D001.md").write_text("# No frontmatter", encoding="utf-8")
        assert load_designs(tmp_path) == []

    def test_skips_template_file(self, tmp_path):
        # Template is D000; glob matches D[0-9]* so D000 would be included
        # but design-template.md won't match D*.md — verify it's excluded
        (tmp_path / "design-template.md").write_text(
            "---\nid: D000\ntitle: Template\nstatus: Draft\n---\n", encoding="utf-8"
        )
        assert load_designs(tmp_path) == []

    def test_unknown_status_sorted_last(self, tmp_path):
        _write_doc(tmp_path, "D002.md", {"id": "D002", "title": "Known", "status": "Draft", "epic": "", "created": "2026-01-01", "updated": "2026-01-01"})
        _write_doc(tmp_path, "D001.md", {"id": "D001", "title": "Unknown", "status": "Weird", "epic": "", "created": "2026-01-01", "updated": "2026-01-01"})
        docs = load_designs(tmp_path)
        assert docs[0]["id"] == "D002"  # Draft (known) first
        assert docs[1]["id"] == "D001"  # Unknown status last


class TestSummaryLines:
    def test_returns_active_statuses_only(self, tmp_path):
        design_dir = tmp_path / "docs" / "focal" / "design"
        design_dir.mkdir(parents=True)
        _write_doc(design_dir, "D001.md", {"id": "D001", "title": "Active one", "status": "Active", "epic": "1", "created": "2026-01-01", "updated": "2026-01-01"})
        _write_doc(design_dir, "D002.md", {"id": "D002", "title": "Done one", "status": "Done", "epic": "2", "created": "2026-01-01", "updated": "2026-01-01"})
        _write_doc(design_dir, "D003.md", {"id": "D003", "title": "Planned one", "status": "Planned", "epic": "3", "created": "2026-01-01", "updated": "2026-01-01"})

        lines = summary_lines(tmp_path)
        ids = [ln.split()[0] for ln in lines]
        assert "D001" in ids
        assert "D003" in ids
        assert "D002" not in ids  # Done is excluded

    def test_returns_empty_when_no_design_dir(self, tmp_path):
        assert summary_lines(tmp_path) == []
