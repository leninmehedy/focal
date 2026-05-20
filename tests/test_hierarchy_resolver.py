"""Tests for hierarchy_resolver.py — resolve() parent mapping."""

from focal.pm.hierarchy_resolver import resolve


def _epic(number: int) -> dict:
    return {"number": number, "title": f"Epic {number}", "body": "", "labels": ["epic"]}


def _story(number: int, title: str = "", body: str = "") -> dict:
    return {
        "number": number,
        "title": title or f"Story {number}",
        "body": body,
        "labels": ["story"],
    }


class TestSubIssuesAPI:
    def test_api_link_resolved(self):
        epics = [_epic(10)]
        stories = [_story(20)]
        result = resolve(epics, stories, sub_issue_map={10: [20]})
        assert result[20] == 10

    def test_api_overrides_body(self):
        # Even if body says "Part of #99", the API binding wins
        epics = [_epic(10), _epic(99)]
        stories = [_story(20, body="Part of #99")]
        result = resolve(epics, stories, sub_issue_map={10: [20]})
        assert result[20] == 10

    def test_story_not_in_any_epic_sub_issues(self):
        epics = [_epic(10)]
        stories = [_story(20)]
        result = resolve(epics, stories, sub_issue_map={10: []})
        assert result[20] is None


class TestBodyMention:
    def test_part_of_pattern(self):
        epics = [_epic(10)]
        stories = [_story(20, body="Part of #10\n\n| SP | 3 |")]
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] == 10

    def test_parent_colon_pattern(self):
        epics = [_epic(10)]
        stories = [_story(20, body="Parent: #10")]
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] == 10

    def test_parent_no_colon(self):
        epics = [_epic(10)]
        stories = [_story(20, body="Parent #10")]
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] == 10

    def test_body_reference_to_non_epic_ignored(self):
        epics = [_epic(10)]
        stories = [_story(20, body="Part of #99")]  # 99 is not an epic
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] is None


class TestTitlePrefix:
    def test_epic_bracket_prefix(self):
        epics = [_epic(10)]
        stories = [_story(20, title="[Epic 10] implement thing")]
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] == 10

    def test_e_colon_prefix(self):
        epics = [_epic(10)]
        stories = [_story(20, title="E10: implement thing")]
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] == 10

    def test_prefix_to_non_epic_ignored(self):
        epics = [_epic(10)]
        stories = [_story(20, title="[Epic 99] something")]
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] is None


class TestOrphaned:
    def test_no_match_returns_none(self):
        epics = [_epic(10)]
        stories = [_story(20, title="plain title", body="no references")]
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] is None

    def test_multiple_stories_some_orphaned(self):
        epics = [_epic(10)]
        stories = [
            _story(20, body="Part of #10"),
            _story(21, body="no parent"),
        ]
        result = resolve(epics, stories, sub_issue_map={})
        assert result[20] == 10
        assert result[21] is None
