"""Tests for EscalationManager."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest

from cronwatch.escalation import EscalationPolicy
from cronwatch.escalation_manager import EscalationManager
from cronwatch.alerter import Alerter


def _dt(offset: float = 0) -> datetime:
    return datetime(2024, 6, 1, 9, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset)


@pytest.fixture
def alerter():
    a = Alerter()
    a.send = MagicMock()
    return a


@pytest.fixture
def manager(alerter):
    return EscalationManager(alerter, default_policy=EscalationPolicy(threshold=3, repeat_every=1))


class TestEscalationManager:
    def test_no_alert_below_threshold(self, manager, alerter):
        manager.on_failure("job1", "missed", _dt(0))
        manager.on_failure("job1", "missed", _dt(1))
        alerter.send.assert_not_called()

    def test_alert_at_threshold(self, manager, alerter):
        for i in range(3):
            manager.on_failure("job1", "missed", _dt(i))
        alerter.send.assert_called_once()
        alert = alerter.send.call_args[0][0]
        assert alert.kind == "escalation"
        assert alert.job == "job1"

    def test_alert_contains_failure_count(self, manager, alerter):
        for i in range(3):
            manager.on_failure("job1", "slow run", _dt(i))
        alert = alerter.send.call_args[0][0]
        assert alert.extra["consecutive_failures"] == 3

    def test_escalation_count_increments(self, manager, alerter):
        for i in range(5):
            manager.on_failure("job1", "err", _dt(i))
        state = manager.state_for("job1")
        assert state.escalation_count == 3  # at 3, 4, 5

    def test_success_resets_state(self, manager, alerter):
        for i in range(3):
            manager.on_failure("job1", "err", _dt(i))
        manager.on_success("job1")
        state = manager.state_for("job1")
        assert state.consecutive_failures == 0
        assert state.escalation_count == 0

    def test_per_job_policy_override(self, alerter):
        manager = EscalationManager(
            alerter,
            default_policy=EscalationPolicy(threshold=5),
        )
        manager.set_policy("critical", EscalationPolicy(threshold=1))
        manager.on_failure("critical", "err", _dt(0))
        alerter.send.assert_called_once()

    def test_independent_job_states(self, manager, alerter):
        for i in range(3):
            manager.on_failure("jobA", "err", _dt(i))
        manager.on_failure("jobB", "err", _dt(0))
        state_b = manager.state_for("jobB")
        assert state_b.consecutive_failures == 1

    def test_all_states_returns_all(self, manager):
        manager.on_failure("x", "e", _dt())
        manager.on_failure("y", "e", _dt())
        states = manager.all_states()
        assert "x" in states and "y" in states
