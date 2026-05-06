"""Tests for cronwatch.watcher."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.alerter import Alerter
from cronwatch.watcher import WatchedJob, Watcher


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


@pytest.fixture()
def alerter():
    a = Alerter()
    a.send = MagicMock()
    return a


@pytest.fixture()
def watcher(alerter):
    w = Watcher(alerter)
    job = WatchedJob("backup", "0 2 * * *", timeout_seconds=600.0, grace_seconds=120.0)
    w.register(job)
    return w


class TestWatcherRegistration:
    def test_register_stores_job(self, watcher):
        assert "backup" in watcher._jobs

    def test_register_creates_tracker(self, watcher):
        assert "backup" in watcher._trackers


class TestWatcherRecordStart:
    def test_record_start_creates_run(self, watcher):
        watcher.record_start("backup", "r1", at=utc(2024, 1, 1, 2, 0, 0))
        run = watcher._trackers["backup"].get_run("r1")
        assert run is not None
        assert run.is_running


class TestWatcherRecordFinish:
    def test_finish_within_timeout_no_alert(self, alerter, watcher):
        watcher.record_start("backup", "r1", at=utc(2024, 1, 1, 2, 0, 0))
        watcher.record_finish("backup", "r1", at=utc(2024, 1, 1, 2, 5, 0))
        alerter.send.assert_not_called()

    def test_finish_exceeding_timeout_sends_slow_alert(self, alerter, watcher):
        watcher.record_start("backup", "r1", at=utc(2024, 1, 1, 2, 0, 0))
        # 601 seconds > 600s timeout
        watcher.record_finish("backup", "r1", at=utc(2024, 1, 1, 2, 10, 1))
        alerter.send.assert_called_once()
        call_kwargs = alerter.send.call_args[1]
        assert call_kwargs["kind"] == "slow"
        assert call_kwargs["job_name"] == "backup"


class TestWatcherCheckMissed:
    def test_no_alert_when_run_started_after_expected(self, alerter, watcher):
        # Last run at 2024-01-01 02:00; next expected 2024-01-02 02:00
        watcher.record_start("backup", "r1", at=utc(2024, 1, 1, 2, 0, 0))
        # Check at 2024-01-02 02:01 but a new run already started
        watcher.record_start("backup", "r2", at=utc(2024, 1, 2, 2, 0, 0))
        watcher.check_missed(now=utc(2024, 1, 2, 2, 3, 0))
        alerter.send.assert_not_called()

    def test_alert_when_grace_elapsed_and_no_new_run(self, alerter, watcher):
        # Last run at 2024-01-01 02:00; next expected 2024-01-02 02:00
        watcher.record_start("backup", "r1", at=utc(2024, 1, 1, 2, 0, 0))
        # Check well past grace period with no new run
        watcher.check_missed(now=utc(2024, 1, 2, 2, 5, 0))
        alerter.send.assert_called_once()
        call_kwargs = alerter.send.call_args[1]
        assert call_kwargs["kind"] == "missed"
        assert call_kwargs["job_name"] == "backup"

    def test_no_alert_within_grace_period(self, alerter, watcher):
        watcher.record_start("backup", "r1", at=utc(2024, 1, 1, 2, 0, 0))
        # Only 60s after expected (grace is 120s)
        watcher.check_missed(now=utc(2024, 1, 2, 2, 1, 0))
        alerter.send.assert_not_called()
