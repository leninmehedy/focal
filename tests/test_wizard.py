"""Tests for wizard.py pure logic — _parse_board_url()."""

import pytest

from focal.wizard import _parse_board_url


class TestParseBoardUrl:
    def test_user_board(self):
        owner, number = _parse_board_url(
            "https://github.com/users/leninmehedy/projects/3"
        )
        assert owner == "leninmehedy"
        assert number == 3

    def test_org_board(self):
        owner, number = _parse_board_url(
            "https://github.com/orgs/hashgraph/projects/12"
        )
        assert owner == "hashgraph"
        assert number == 12

    def test_strips_trailing_whitespace(self):
        owner, number = _parse_board_url(
            "  https://github.com/users/alice/projects/7  "
        )
        assert owner == "alice"
        assert number == 7

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Could not parse"):
            _parse_board_url("https://github.com/leninmehedy/focal")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _parse_board_url("")

    def test_number_returned_as_int(self):
        _, number = _parse_board_url("https://github.com/users/alice/projects/42")
        assert isinstance(number, int)
