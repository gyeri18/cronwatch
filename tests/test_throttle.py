"""Tests for cronwatch.throttle."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from cronwatch.throttle import AlertThrottle, ThrottleState


def _dt(offset_seconds: float = 0.0) -> datetime:
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(seconds=offset_seconds)


# ---------------------------------------------------------------------------
# ThrottleState unit tests
# ---------------------------------------------------------------------------

class TestThrottleState:
    def test_should_send_when_never_sent(self):
        state = ThrottleState()
        assert state.should_send(_dt(), min_interval_seconds=60) is True

    def test_should_send_after_interval_elapsed(self):
        state = ThrottleState(last_sent=_dt(0))
        assert state.should_send(_dt(61), min_interval_seconds=60) is True

    def test_should_not_send_before_interval_elapsed(self):
        state = ThrottleState(last_sent=_dt(0))
        assert state.should_send(_dt(30), min_interval_seconds=60) is False

    def test_record_sent_resets_suppressed_count(self):
        state = ThrottleState()
        state.record_suppressed()
        state.record_suppressed()
        state.record_sent(_dt())
        assert state.suppressed_count == 0

    def test_record_suppressed_increments(self):
        state = ThrottleState()
        state.record_suppressed()
        state.record_suppressed()
        assert state.suppressed_count == 2


# ---------------------------------------------------------------------------
# AlertThrottle integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def throttle() -> AlertThrottle:
    return AlertThrottle(default_interval_seconds=300.0)


class TestAlertThrottle:
    def test_first_alert_always_allowed(self, throttle):
        assert throttle.allow("missed", "backup") is True

    def test_second_alert_suppressed_within_interval(self, throttle):
        throttle.allow("missed", "backup")
        assert throttle.allow("missed", "backup") is False

    def test_suppressed_count_increments(self, throttle):
        throttle.allow("missed", "backup")
        throttle.allow("missed", "backup")
        throttle.allow("missed", "backup")
        assert throttle.suppressed_count("missed", "backup") == 2

    def test_custom_rule_overrides_default(self, throttle):
        throttle.set_rule("slow", "etl", min_interval_seconds=0)
        throttle.allow("slow", "etl")
        assert throttle.allow("slow", "etl") is True

    def test_different_jobs_tracked_independently(self, throttle):
        throttle.allow("missed", "job_a")
        assert throttle.allow("missed", "job_b") is True

    def test_different_kinds_tracked_independently(self, throttle):
        throttle.allow("missed", "backup")
        assert throttle.allow("slow", "backup") is True

    def test_reset_clears_state(self, throttle):
        throttle.allow("missed", "backup")
        throttle.reset("missed", "backup")
        assert throttle.allow("missed", "backup") is True

    def test_suppressed_count_zero_for_unknown_key(self, throttle):
        assert throttle.suppressed_count("missed", "unknown") == 0
