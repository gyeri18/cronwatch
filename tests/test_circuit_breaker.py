"""Tests for circuit_breaker.py and alerter_circuit_broken.py."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerter import Alert
from cronwatch.alerter_circuit_broken import CircuitBrokenAlerter
from cronwatch.circuit_breaker import CircuitBreaker, State


# ---------------------------------------------------------------------------
# CircuitBreaker unit tests
# ---------------------------------------------------------------------------

class TestCircuitBreakerInit:
    def test_defaults_accepted(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == 3
        assert cb.state is State.CLOSED

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreaker(failure_threshold=0)

    def test_invalid_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreaker(recovery_timeout=0)


class TestCircuitBreakerTransitions:
    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        assert cb.state is State.CLOSED
        cb.record_failure()
        assert cb.state is State.OPEN

    def test_allow_request_false_when_open(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert not cb.allow_request()

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.06)
        assert cb.state is State.HALF_OPEN
        assert cb.allow_request()

    def test_success_closes_from_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.06)
        cb.record_success()
        assert cb.state is State.CLOSED

    def test_failure_in_half_open_reopens(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.06)
        _ = cb.state  # trigger transition to HALF_OPEN
        cb.record_failure()
        assert cb.state is State.OPEN

    def test_reset_clears_state(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        cb.reset()
        assert cb.state is State.CLOSED
        assert cb._failures == 0


# ---------------------------------------------------------------------------
# CircuitBrokenAlerter integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def alert():
    return Alert(kind="missed", job="nightly", message="overdue")


class TestCircuitBrokenAlerter:
    def test_sends_to_healthy_handler(self, alert):
        handler = MagicMock()
        a = CircuitBrokenAlerter()
        a.add_handler(handler)
        result = a.send(alert)
        handler.assert_called_once_with(alert)
        assert list(result.values())[0] == "sent"

    def test_skips_open_circuit(self, alert):
        handler = MagicMock(side_effect=RuntimeError("down"))
        a = CircuitBrokenAlerter(failure_threshold=1)
        a.add_handler(handler)
        a.send(alert)  # opens circuit
        handler.reset_mock()
        result = a.send(alert)
        handler.assert_not_called()
        assert list(result.values())[0] == "open"

    def test_error_result_on_failure(self, alert):
        handler = MagicMock(side_effect=ValueError("boom"))
        a = CircuitBrokenAlerter(failure_threshold=5)
        a.add_handler(handler)
        result = a.send(alert)
        assert "error" in list(result.values())[0]

    def test_reset_all_reopens_handlers(self, alert):
        handler = MagicMock(side_effect=RuntimeError)
        a = CircuitBrokenAlerter(failure_threshold=1)
        a.add_handler(handler)
        a.send(alert)
        a.reset_all()
        assert a.breaker_for(handler).state is State.CLOSED
