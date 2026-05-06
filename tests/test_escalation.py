"""Tests for EscalationPolicy and EscalationState."""
from datetime import datetime, timezone, timedelta
import pytest

from cronwatch.escalation import EscalationPolicy, EscalationState


def _dt(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds)


class TestEscalationPolicy:
    def test_no_escalation_below_threshold(self):
        policy = EscalationPolicy(threshold=3)
        state = EscalationState(job_name="job")
        state.record_failure(_dt(0))
        state.record_failure(_dt(1))
        assert not policy.should_escalate(state)

    def test_escalates_at_threshold(self):
        policy = EscalationPolicy(threshold=3)
        state = EscalationState(job_name="job")
        for i in range(3):
            state.record_failure(_dt(i))
        assert policy.should_escalate(state)

    def test_repeat_every_respected(self):
        policy = EscalationPolicy(threshold=2, repeat_every=2)
        state = EscalationState(job_name="job")
        for i in range(3):
            state.record_failure(_dt(i))
        # 3 failures: excess=1, 1 % 2 != 0 → no escalation
        assert not policy.should_escalate(state)
        state.record_failure(_dt(4))
        # 4 failures: excess=2, 2 % 2 == 0 → escalate
        assert policy.should_escalate(state)

    def test_min_window_blocks_early_escalation(self):
        policy = EscalationPolicy(threshold=2, min_window_seconds=60.0)
        state = EscalationState(job_name="job")
        state.record_failure(_dt(0))
        state.record_failure(_dt(10))  # only 10s window
        assert not policy.should_escalate(state)

    def test_min_window_allows_after_elapsed(self):
        policy = EscalationPolicy(threshold=2, min_window_seconds=60.0)
        state = EscalationState(job_name="job")
        state.record_failure(_dt(0))
        state.record_failure(_dt(90))  # 90s window
        assert policy.should_escalate(state)


class TestEscalationState:
    def test_initial_state(self):
        state = EscalationState(job_name="myjob")
        assert state.consecutive_failures == 0
        assert state.escalation_count == 0
        assert state.first_failure_at is None

    def test_record_failure_increments(self):
        state = EscalationState(job_name="myjob")
        state.record_failure(_dt(0))
        assert state.consecutive_failures == 1
        assert state.first_failure_at == _dt(0)

    def test_record_failure_preserves_first(self):
        state = EscalationState(job_name="myjob")
        state.record_failure(_dt(0))
        state.record_failure(_dt(5))
        assert state.first_failure_at == _dt(0)
        assert state.last_failure_at == _dt(5)

    def test_record_success_resets(self):
        state = EscalationState(job_name="myjob")
        state.record_failure(_dt(0))
        state.record_failure(_dt(1))
        state.record_success()
        assert state.consecutive_failures == 0
        assert state.first_failure_at is None
        assert state.escalation_count == 0

    def test_window_seconds(self):
        state = EscalationState(job_name="myjob")
        state.record_failure(_dt(0))
        state.record_failure(_dt(30))
        assert state.window_seconds() == 30.0

    def test_to_dict_keys(self):
        state = EscalationState(job_name="myjob")
        d = state.to_dict()
        assert "job_name" in d
        assert "consecutive_failures" in d
        assert "escalation_count" in d
