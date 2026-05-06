"""Tests for cronwatch.alerter (including throttle integration)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerter import Alert, Alerter
from cronwatch.throttle import AlertThrottle


@pytest.fixture()
def alerter() -> Alerter:
    return Alerter()


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------

class TestAlert:
    def test_str_contains_kind_and_job(self):
        a = Alert(kind="missed", job_name="backup", message="not run")
        assert "MISSED" in str(a)
        assert "backup" in str(a)

    def test_str_contains_message(self):
        a = Alert(kind="slow", job_name="etl", message="too slow")
        assert "too slow" in str(a)


# ---------------------------------------------------------------------------
# Alerter handler management
# ---------------------------------------------------------------------------

class TestAlerterHandlers:
    def test_handler_called_on_alert(self, alerter):
        handler = MagicMock()
        alerter.add_handler(handler)
        alerter.send(Alert("missed", "backup", "msg"))
        handler.assert_called_once()

    def test_multiple_handlers_all_called(self, alerter):
        h1, h2 = MagicMock(), MagicMock()
        alerter.add_handler(h1)
        alerter.add_handler(h2)
        alerter.send(Alert("missed", "backup", "msg"))
        h1.assert_called_once()
        h2.assert_called_once()

    def test_handler_count(self, alerter):
        alerter.add_handler(MagicMock())
        alerter.add_handler(MagicMock())
        assert alerter.handler_count == 2

    def test_faulty_handler_does_not_raise(self, alerter):
        alerter.add_handler(lambda a: (_ for _ in ()).throw(RuntimeError("boom")))
        alerter.send(Alert("missed", "backup", "msg"))  # should not raise

    def test_sent_count_increments(self, alerter):
        alerter.add_handler(MagicMock())
        alerter.send(Alert("missed", "backup", "m"))
        alerter.send(Alert("slow", "etl", "m"))
        assert alerter.sent_count == 2


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

class TestAlerterHelpers:
    def test_alert_missed_dispatches(self, alerter):
        h = MagicMock()
        alerter.add_handler(h)
        result = alerter.alert_missed("backup")
        assert result is True
        assert h.call_args[0][0].kind == "missed"

    def test_alert_slow_dispatches(self, alerter):
        h = MagicMock()
        alerter.add_handler(h)
        alerter.alert_slow("etl")
        assert h.call_args[0][0].kind == "slow"

    def test_alert_recovered_dispatches(self, alerter):
        h = MagicMock()
        alerter.add_handler(h)
        alerter.alert_recovered("etl")
        assert h.call_args[0][0].kind == "recovered"


# ---------------------------------------------------------------------------
# Throttle integration
# ---------------------------------------------------------------------------

class TestAlerterThrottle:
    def test_throttled_alert_returns_false(self):
        throttle = AlertThrottle(default_interval_seconds=9999)
        a = Alerter(throttle=throttle)
        a.add_handler(MagicMock())
        a.send(Alert("missed", "backup", "first"))
        result = a.send(Alert("missed", "backup", "second"))
        assert result is False

    def test_suppressed_count_increments(self):
        throttle = AlertThrottle(default_interval_seconds=9999)
        a = Alerter(throttle=throttle)
        a.send(Alert("missed", "backup", "first"))
        a.send(Alert("missed", "backup", "second"))
        a.send(Alert("missed", "backup", "third"))
        assert a.suppressed_count == 2

    def test_no_throttle_always_sends(self):
        a = Alerter(throttle=None)
        h = MagicMock()
        a.add_handler(h)
        for _ in range(5):
            a.send(Alert("missed", "backup", "msg"))
        assert h.call_count == 5
