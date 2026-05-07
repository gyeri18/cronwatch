"""Tests for cronwatch.snapshot."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.snapshot import JobSnapshot, SnapshotCollector, WatcherSnapshot


def _dt(hour: int = 12) -> datetime:
    return datetime(2024, 1, 15, hour, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# JobSnapshot
# ---------------------------------------------------------------------------

class TestJobSnapshot:
    def _make(self, **kwargs) -> JobSnapshot:
        defaults = dict(
            name="backup",
            schedule="0 2 * * *",
            last_start=_dt(2),
            last_finish=_dt(3),
            last_exit_code=0,
            is_running=False,
            total_runs=5,
            missed_count=1,
        )
        defaults.update(kwargs)
        return JobSnapshot(**defaults)

    def test_to_dict_contains_name(self):
        snap = self._make(name="backup")
        assert snap.to_dict()["name"] == "backup"

    def test_to_dict_isoformat_dates(self):
        snap = self._make(last_start=_dt(2), last_finish=_dt(3))
        d = snap.to_dict()
        assert "2024-01-15T02" in d["last_start"]
        assert "2024-01-15T03" in d["last_finish"]

    def test_to_dict_none_dates_when_absent(self):
        snap = self._make(last_start=None, last_finish=None)
        d = snap.to_dict()
        assert d["last_start"] is None
        assert d["last_finish"] is None

    def test_to_dict_includes_counts(self):
        snap = self._make(total_runs=7, missed_count=2)
        d = snap.to_dict()
        assert d["total_runs"] == 7
        assert d["missed_count"] == 2


# ---------------------------------------------------------------------------
# WatcherSnapshot
# ---------------------------------------------------------------------------

class TestWatcherSnapshot:
    def _snap(self) -> WatcherSnapshot:
        jobs = [
            JobSnapshot("alpha", "* * * * *", None, None, None, False, 0, 0),
            JobSnapshot("beta", "0 * * * *", _dt(), None, None, True, 3, 0),
        ]
        return WatcherSnapshot(captured_at=_dt(12), jobs=jobs)

    def test_to_dict_captured_at_present(self):
        d = self._snap().to_dict()
        assert "captured_at" in d
        assert "2024-01-15T12" in d["captured_at"]

    def test_to_dict_jobs_list(self):
        d = self._snap().to_dict()
        assert len(d["jobs"]) == 2

    def test_job_lookup_by_name(self):
        snap = self._snap()
        assert snap.job("beta").is_running is True

    def test_job_lookup_missing_returns_none(self):
        assert self._snap().job("nonexistent") is None


# ---------------------------------------------------------------------------
# SnapshotCollector
# ---------------------------------------------------------------------------

class TestSnapshotCollector:
    def _make_watcher(self, job_names, runs_map=None, missed_map=None):
        runs_map = runs_map or {}
        missed_map = missed_map or {}

        tracker = MagicMock()
        tracker.runs.side_effect = lambda name: runs_map.get(name, [])
        tracker.missed_count.side_effect = lambda name: missed_map.get(name, 0)

        watcher = MagicMock()
        watcher.tracker = tracker

        jobs = {}
        for name in job_names:
            cfg = MagicMock()
            cfg.name = name
            cfg.schedule = "* * * * *"
            watched = MagicMock()
            watched.config = cfg
            jobs[name] = watched
        watcher.jobs = jobs
        return watcher

    def test_collect_returns_watcher_snapshot(self):
        watcher = self._make_watcher(["myjob"])
        collector = SnapshotCollector(watcher)
        snap = collector.collect()
        assert isinstance(snap, WatcherSnapshot)

    def test_collect_one_job_per_registered(self):
        watcher = self._make_watcher(["a", "b", "c"])
        snap = SnapshotCollector(watcher).collect()
        assert len(snap.jobs) == 3

    def test_collect_no_runs_gives_none_dates(self):
        watcher = self._make_watcher(["empty"])
        snap = SnapshotCollector(watcher).collect()
        js = snap.job("empty")
        assert js.last_start is None
        assert js.total_runs == 0

    def test_collect_uses_last_run_data(self):
        run = MagicMock()
        run.started_at = _dt(5)
        run.finished_at = _dt(6)
        run.exit_code = 0
        run.is_running.return_value = False
        watcher = self._make_watcher(["job1"], runs_map={"job1": [run]})
        snap = SnapshotCollector(watcher).collect()
        js = snap.job("job1")
        assert js.last_start == _dt(5)
        assert js.total_runs == 1

    def test_collect_missed_count_propagated(self):
        watcher = self._make_watcher(["flaky"], missed_map={"flaky": 4})
        snap = SnapshotCollector(watcher).collect()
        assert snap.job("flaky").missed_count == 4
