"""Tests for cronwatch.alerter (including retry integration)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from cronwatch.alerter import Alert, Alerter
from cronwatch.retry import RetryPolicy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def alerter() -> Alerter:
    return Alerter()


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

class TestAlert:
    def test_str_contains_kind_and_job(self):
        a = Alert(kind="missed", job_name="backup", message="overdue")
        assert "MISSED" in str(a)
        assert "backup" in str(a)

    def test_str_contains_message(self):
        a = Alert(kind="slow", job_name="sync", message="took 120s")
        assert "took 120s" in str(a)

    def test_extra_defaults_to_empty_dict(self):
        a = Alert(kind="error", job_name="j", message="m")
        assert a.extra == {}


# ---------------------------------------------------------------------------
# Alerter handlers
# ---------------------------------------------------------------------------

class TestAlerterHandlers:
    def test_add_handler_receives_alert(self, alerter):
        received = []
        alerter.add_handler(received.append)
        alerter.send(Alert("missed", "job", "msg"))
        assert len(received) == 1

    def test_multiple_handlers_all_called(self, alerter):
        h1, h2 = MagicMock(), MagicMock()
        alerter.add_handler(h1)
        alerter.add_handler(h2)
        alerter.send(Alert("slow", "job", "msg"))
        h1.assert_called_once()
        h2.assert_called_once()

    def test_remove_handler_stops_delivery(self, alerter):
        received = []
        alerter.add_handler(received.append)
        alerter.remove_handler(received.append)
        alerter.send(Alert("missed", "job", "msg"))
        assert received == []

    def test_remove_missing_handler_is_noop(self, alerter):
        alerter.remove_handler(lambda a: None)  # should not raise

    def test_no_handlers_does_not_raise(self, alerter):
        alerter.send(Alert("error", "job", "msg"))  # should not raise


# ---------------------------------------------------------------------------
# Convenience methods
# ---------------------------------------------------------------------------

class TestAlerterConvenience:
    def test_missed_sends_correct_kind(self, alerter):
        received = []
        alerter.add_handler(received.append)
        alerter.missed("backup", "overdue by 5 min")
        assert received[0].kind == "missed"
        assert received[0].job_name == "backup"

    def test_slow_sends_correct_kind(self, alerter):
        received = []
        alerter.add_handler(received.append)
        alerter.slow("sync", "took 200s")
        assert received[0].kind == "slow"

    def test_error_sends_correct_kind(self, alerter):
        received = []
        alerter.add_handler(received.append)
        alerter.error("deploy", "exit code 1")
        assert received[0].kind == "error"


# ---------------------------------------------------------------------------
# Retry integration
# ---------------------------------------------------------------------------

class TestAlerterRetry:
    def test_handler_retried_on_failure(self):
        policy = RetryPolicy(max_attempts=3, base_delay=0.0)
        alerter = Alerter(retry_policy=policy)

        calls = []
        side_effects = [RuntimeError("fail"), None]

        def flaky(alert):
            calls.append(alert)
            effect = side_effects.pop(0)
            if effect is not None:
                raise effect

        alerter.add_handler(flaky)
        alerter.send(Alert("missed", "job", "msg"))
        assert len(calls) == 2

    def test_failed_handler_logs_error(self, caplog):
        import logging
        policy = RetryPolicy(max_attempts=1, base_delay=0.0)
        alerter = Alerter(retry_policy=policy)
        alerter.add_handler(MagicMock(side_effect=RuntimeError("boom")))
        with caplog.at_level(logging.ERROR, logger="cronwatch.alerter"):
            alerter.send(Alert("error", "job", "msg"))
        assert any("failed" in r.message for r in caplog.records)
