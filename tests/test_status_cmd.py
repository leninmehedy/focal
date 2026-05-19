"""Tests for status_cmd pure logic — _current_iteration(), _days_remaining(), _project_delivery()."""

from datetime import date, timedelta

from focal.pm.status_cmd import _current_iteration, _days_remaining, _project_delivery


def _iter(label, start, end):
    return {"label": label, "start": str(start), "end": str(end), "story_ids": []}


TODAY = date.today()


class TestCurrentIteration:
    def test_returns_active_iteration(self):
        iterations = [
            _iter("I1", TODAY - timedelta(days=10), TODAY - timedelta(days=1)),
            _iter("I2", TODAY - timedelta(days=0), TODAY + timedelta(days=9)),
            _iter("I3", TODAY + timedelta(days=10), TODAY + timedelta(days=19)),
        ]
        result = _current_iteration({"iterations": iterations})
        assert result["label"] == "I2"

    def test_returns_last_when_all_past(self):
        iterations = [
            _iter("I1", TODAY - timedelta(days=20), TODAY - timedelta(days=11)),
            _iter("I2", TODAY - timedelta(days=10), TODAY - timedelta(days=1)),
        ]
        result = _current_iteration({"iterations": iterations})
        assert result["label"] == "I2"

    def test_returns_none_when_empty(self):
        assert _current_iteration({"iterations": []}) is None

    def test_returns_none_when_no_iterations_key(self):
        assert _current_iteration({}) is None

    def test_iteration_starting_today(self):
        iterations = [_iter("I1", TODAY, TODAY + timedelta(days=9))]
        result = _current_iteration({"iterations": iterations})
        assert result["label"] == "I1"

    def test_iteration_ending_today(self):
        iterations = [_iter("I1", TODAY - timedelta(days=9), TODAY)]
        result = _current_iteration({"iterations": iterations})
        assert result["label"] == "I1"


class TestDaysRemaining:
    def test_future_end(self):
        it = _iter("I1", TODAY, TODAY + timedelta(days=5))
        assert _days_remaining(it) == 5

    def test_ends_today(self):
        it = _iter("I1", TODAY - timedelta(days=9), TODAY)
        assert _days_remaining(it) == 0

    def test_past_end_clamps_to_zero(self):
        it = _iter("I1", TODAY - timedelta(days=10), TODAY - timedelta(days=1))
        assert _days_remaining(it) == 0


class TestProjectDelivery:
    def test_halfway_through_on_track(self):
        # 5 of 10 SP delivered, 5 of 10 days elapsed, 5 remaining
        result = _project_delivery(
            delivered_sp=5, total_sp=10, days_remaining=5, total_days=10
        )
        assert result == 10  # on track for 100%

    def test_no_days_elapsed_returns_zero(self):
        result = _project_delivery(
            delivered_sp=0, total_sp=10, days_remaining=10, total_days=10
        )
        assert result == 0

    def test_all_delivered_returns_total(self):
        result = _project_delivery(
            delivered_sp=10, total_sp=10, days_remaining=0, total_days=10
        )
        assert result == 10

    def test_projection_capped_at_total(self):
        # Overperforming — shouldn't project more than total_sp
        result = _project_delivery(
            delivered_sp=9, total_sp=10, days_remaining=5, total_days=6
        )
        assert result == 10

    def test_zero_total_sp_returns_delivered(self):
        result = _project_delivery(
            delivered_sp=0, total_sp=0, days_remaining=5, total_days=10
        )
        assert result == 0

    def test_zero_total_days_returns_delivered(self):
        result = _project_delivery(
            delivered_sp=3, total_sp=10, days_remaining=0, total_days=0
        )
        assert result == 3
