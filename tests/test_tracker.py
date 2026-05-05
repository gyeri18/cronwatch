"""Tests for cronwatch.tracker module."""

import time
import pytest

from cronwatch.schedule import CronSchedule
from cronwatch.tracker import JobRun, JobTracker


EVERY_MINUTE = "* * * * *"


@pytest.fixture
def tracker():
    schedule = CronSchedule(EVERY_MINUTE)
    return JobTracker(name="test-job", schedule=schedule, timeout_seconds=10.0)


class TestJobRun:
    def test_duration_none_while_running(self):
        run = JobRun(started_at=1000.0)
        assert run.duration is None

    def test_duration_calculated_after_finish(self):
        run = JobRun(started_at=1000.0, finished_at=1005.0)
        assert run.duration == pytest.approx(5.0)

    def test_is_running_true_before_finish(self):
        run = JobRun(started_at=1000.0)
        assert run.is_running is True

    def test_is_running_false_after_finish(self):
        run = JobRun(started_at=1000.0, finished_at=1001.0)
        assert run.is_running is False


class TestJobTracker:
    def test_record_start_creates_run(self, tracker):
        run = tracker.record_start(timestamp=1000.0)
        assert run.started_at == 1000.0
        assert run.is_running is True
        assert tracker.last_run is run

    def test_record_finish_closes_run(self, tracker):
        tracker.record_start(timestamp=1000.0)
        run = tracker.record_finish(timestamp=1003.0)
        assert run is not None
        assert run.finished_at == 1003.0
        assert run.duration == pytest.approx(3.0)

    def test_record_finish_without_start_returns_none(self, tracker):
        result = tracker.record_finish()
        assert result is None

    def test_history_accumulates(self, tracker):
        tracker.record_start(timestamp=1000.0)
        tracker.record_finish(timestamp=1001.0)
        tracker.record_start(timestamp=1062.0)
        tracker.record_finish(timestamp=1063.0)
        assert len(tracker.history) == 2

    def test_is_slow_false_when_not_running(self, tracker):
        assert tracker.is_slow() is False

    def test_is_slow_true_after_timeout(self, tracker):
        past = time.time() - 20.0
        tracker.record_start(timestamp=past)
        assert tracker.is_slow() is True

    def test_is_slow_false_within_timeout(self, tracker):
        recent = time.time() - 2.0
        tracker.record_start(timestamp=recent)
        assert tracker.is_slow() is False

    def test_is_missed_true_with_no_history(self, tracker):
        # Provide a reference time well past the epoch so next_run returns something
        ref = time.time()
        # Without any runs, job should be considered missed
        assert tracker.is_missed(reference_time=ref) is True

    def test_is_missed_false_after_recent_run(self, tracker):
        now = time.time()
        # Simulate a run that just happened
        tracker.record_start(timestamp=now - 5)
        tracker.record_finish(timestamp=now - 1)
        assert tracker.is_missed(reference_time=now) is False
