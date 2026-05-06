"""Tests for cronwatch.reporter module."""

import pytest

from cronwatch.history import HistoryEntry, JobHistory
from cronwatch.reporter import JobSummary, Reporter


def _entry(name="backup", status="success", duration=10.0):
    return HistoryEntry(
        job_name=name,
        started_at="2024-01-01T00:00:00",
        finished_at="2024-01-01T00:00:10",
        duration_seconds=duration,
        exit_code=0 if status == "success" else 1,
        status=status,
    )


@pytest.fixture
def history(tmp_path):
    h = JobHistory(str(tmp_path / "hist.json"))
    h.record(_entry("backup", "success", 10.0))
    h.record(_entry("backup", "success", 20.0))
    h.record(_entry("backup", "failure", 5.0))
    h.record(_entry("backup", "missed", None))
    h.record(_entry("backup", "slow", 60.0))
    h.record(_entry("cleanup", "success", 3.0))
    return h


@pytest.fixture
def reporter(history):
    return Reporter(history)


class TestJobSummary:
    def test_success_rate_full(self):
        s = JobSummary("j", 4, 4, 0, 0, 0, 1.0, 1.0)
        assert s.success_rate == 1.0

    def test_success_rate_zero_runs(self):
        s = JobSummary("j", 0, 0, 0, 0, 0, None, None)
        assert s.success_rate == 0.0

    def test_success_rate_partial(self):
        s = JobSummary("j", 4, 2, 2, 0, 0, 1.0, 1.0)
        assert s.success_rate == 0.5


class TestReporter:
    def test_summarize_counts(self, reporter):
        s = reporter.summarize("backup")
        assert s.total_runs == 5
        assert s.success_count == 2
        assert s.failure_count == 1
        assert s.missed_count == 1
        assert s.slow_count == 1

    def test_summarize_avg_duration(self, reporter):
        s = reporter.summarize("backup")
        # durations with values: 10, 20, 5, 60 (missed has None)
        assert s.avg_duration == pytest.approx((10 + 20 + 5 + 60) / 4)

    def test_summarize_max_duration(self, reporter):
        s = reporter.summarize("backup")
        assert s.max_duration == pytest.approx(60.0)

    def test_summarize_unknown_job_empty(self, reporter):
        s = reporter.summarize("nonexistent")
        assert s.total_runs == 0
        assert s.avg_duration is None

    def test_format_summary_contains_job_name(self, reporter):
        s = reporter.summarize("backup")
        text = reporter.format_summary(s)
        assert "backup" in text
        assert "Success" in text

    def test_format_summary_shows_duration(self, reporter):
        s = reporter.summarize("backup")
        text = reporter.format_summary(s)
        assert "Avg dur" in text
        assert "Max dur" in text

    def test_all_summaries_returns_all_jobs(self, reporter):
        summaries = reporter.all_summaries()
        names = [s.job_name for s in summaries]
        assert "backup" in names
        assert "cleanup" in names
