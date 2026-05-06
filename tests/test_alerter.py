"""Tests for cronwatch.alerter."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatch.alerter import Alert, Alerter


@pytest.fixture()
def alerter() -> Alerter:
    return Alerter(slow_threshold=timedelta(minutes=5))


class TestAlert:
    def test_str_contains_kind_and_job(self):
        a = Alert(job_name="backup", kind="missed", message="too late")
        text = str(a)
        assert "MISSED" in text
        assert "backup" in text
        assert "too late" in text


class TestAlerterHandlers:
    def test_handler_called_on_alert(self, alerter):
        handler = MagicMock()
        alerter.add_handler(handler)
        alerter.check_failed("myjob", exit_code=1)
        handler.assert_called_once()
        alert = handler.call_args[0][0]
        assert isinstance(alert, Alert)
        assert alert.kind == "failed"

    def test_multiple_handlers_all_called(self, alerter):
        h1, h2 = MagicMock(), MagicMock()
        alerter.add_handler(h1)
        alerter.add_handler(h2)
        alerter.check_failed("job", exit_code=2)
        h1.assert_called_once()
        h2.assert_called_once()

    def test_alert_stored_in_history(self, alerter):
        alerter.check_failed("job", exit_code=1)
        assert len(alerter.history) == 1
        assert alerter.history[0].kind == "failed"


class TestCheckFailed:
    def test_zero_exit_code_no_alert(self, alerter):
        assert alerter.check_failed("job", 0) is False
        assert alerter.history == []

    def test_nonzero_exit_code_fires_alert(self, alerter):
        assert alerter.check_failed("job", 1) is True
        assert alerter.history[0].job_name == "job"


class TestCheckSlow:
    def test_under_threshold_no_alert(self, alerter):
        assert alerter.check_slow("job", timedelta(minutes=3)) is False
        assert alerter.history == []

    def test_over_threshold_fires_alert(self, alerter):
        assert alerter.check_slow("job", timedelta(minutes=10)) is True
        assert alerter.history[0].kind == "slow"

    def test_alert_message_contains_duration(self, alerter):
        alerter.check_slow("job", timedelta(minutes=10))
        assert "0:10:00" in alerter.history[0].message


class TestCheckMissed:
    def test_future_expected_no_alert(self, alerter):
        future = datetime.utcnow() + timedelta(hours=1)
        assert alerter.check_missed("job", expected_at=future) is False
        assert alerter.history == []

    def test_past_expected_fires_alert(self, alerter):
        past = datetime.utcnow() - timedelta(hours=1)
        assert alerter.check_missed("job", expected_at=past) is True
        assert alerter.history[0].kind == "missed"

    def test_within_grace_no_alert(self, alerter):
        # just missed but within grace
        slightly_past = datetime.utcnow() - timedelta(seconds=10)
        assert (
            alerter.check_missed("job", slightly_past, grace=timedelta(minutes=5))
            is False
        )
