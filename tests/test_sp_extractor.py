"""Tests for sp_extractor.py — extract_sp() priority chain."""

from focal.pm.sp_extractor import extract_sp


def _issue(title: str = "", body: str = "") -> dict:
    return {"title": title, "body": body}


class TestProjectFieldPriority:
    def test_project_field_wins_over_title(self):
        assert extract_sp(_issue(title="[5]"), project_field_value=13) == 13

    def test_project_field_wins_over_body(self):
        issue = _issue(body="| SP | 8 |\n|---|---|")
        assert extract_sp(issue, project_field_value=3) == 3

    def test_project_field_zero_is_valid(self):
        assert extract_sp(_issue(), project_field_value=0) == 0


class TestTitlePatterns:
    def test_bracket_notation(self):
        assert extract_sp(_issue(title="[13] My story")) == 13

    def test_paren_sp_notation(self):
        assert extract_sp(_issue(title="My story (5 SP)")) == 5

    def test_paren_sp_case_insensitive(self):
        assert extract_sp(_issue(title="My story (5 sp)")) == 5

    def test_bare_number_sp(self):
        assert extract_sp(_issue(title="My story 8SP")) == 8

    def test_hash_number_sp(self):
        assert extract_sp(_issue(title="#3SP fix thing")) == 3

    def test_no_match_returns_none(self):
        assert extract_sp(_issue(title="Plain title with no SP")) is None


class TestBodyTable:
    def test_sp_row(self):
        body = "Some text\n\n| SP | 5 |\n|---|---|\n"
        assert extract_sp(_issue(body=body)) == 5

    def test_story_points_row(self):
        body = "| Story Points | 8 |\n|---|---|\n"
        assert extract_sp(_issue(body=body)) == 8

    def test_case_insensitive(self):
        body = "| story points | 3 |\n|---|---|\n"
        assert extract_sp(_issue(body=body)) == 3

    def test_no_table_returns_none(self):
        assert extract_sp(_issue(body="Just prose text.")) is None


class TestBodyProse:
    def test_bold_estimated(self):
        assert extract_sp(_issue(body="**Estimated:** 5 SP")) == 5

    def test_plain_estimated(self):
        assert extract_sp(_issue(body="Estimated: 7 SP")) == 7

    def test_case_insensitive(self):
        assert extract_sp(_issue(body="estimated: 3 sp")) == 3

    def test_table_beats_prose(self):
        body = "| SP | 10 |\n|---|---|\n**Estimated:** 3 SP"
        assert extract_sp(_issue(body=body)) == 10

    def test_no_match_returns_none(self):
        assert extract_sp(_issue(body="Some prose without estimate.")) is None


class TestFallback:
    def test_none_when_nothing_found(self):
        assert extract_sp(_issue(title="Plain", body="No SP here")) is None

    def test_title_beats_body(self):
        # Title pattern should match before body table
        issue = _issue(title="[3] story", body="| SP | 99 |\n|---|---|")
        assert extract_sp(issue) == 3
