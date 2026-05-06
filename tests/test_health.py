"""Tests for cronwatch.health module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.health import HealthChecker, HealthStatus


def _make_metrics(total=0, slow=0, missed=0, success_rate=1.0, avg=None, max_=None):
    m = MagicMock()
    m.total_runs = total
    m.slow_runs = slow
    m.missed_runs = missed
    m.success_rate = success_rate
    m.avg_duration = avg
    m.max_duration = max_
    return m


@pytest.fixture()
def daemon():
    d = MagicMock()
    d.running = True
    d.uptime_seconds = 42.0
    return d


class TestHealthStatus:
    def test_healthy_when_running_and_no_failures(self):
        status = HealthStatus(running=True, uptime_seconds=10.0, job_statuses={})
        assert status.healthy is True

    def test_unhealthy_when_not_running(self):
        status = HealthStatus(running=False, uptime_seconds=None, job_statuses={})
        assert status.healthy is False

    def test_unhealthy_when_job_has_zero_success_rate(self):
        job_statuses = {"myjob": {"total_runs": 5, "success_rate": 0.0}}
        status = HealthStatus(running=True, uptime_seconds=5.0, job_statuses=job_statuses)
        assert status.healthy is False

    def test_healthy_when_job_has_no_runs_yet(self):
        job_statuses = {"myjob": {"total_runs": 0, "success_rate": 0.0}}
        status = HealthStatus(running=True, uptime_seconds=1.0, job_statuses=job_statuses)
        assert status.healthy is True

    def test_to_dict_contains_expected_keys(self):
        status = HealthStatus(running=True, uptime_seconds=7.5, job_statuses={"j": {"total_runs": 1}})
        d = status.to_dict()
        assert "healthy" in d
        assert "running" in d
        assert "uptime_seconds" in d
        assert "checked_at" in d
        assert "jobs" in d

    def test_to_json_is_valid_json(self):
        status = HealthStatus(running=True, uptime_seconds=3.0, job_statuses={})
        raw = status.to_json()
        parsed = json.loads(raw)
        assert parsed["running"] is True

    def test_checked_at_defaults_to_now(self):
        before = datetime.now(timezone.utc)
        status = HealthStatus(running=True, uptime_seconds=0.0, job_statuses={})
        after = datetime.now(timezone.utc)
        assert before <= status.checked_at <= after


class TestHealthChecker:
    def test_check_returns_health_status(self, daemon):
        checker = HealthChecker(daemon, {})
        result = checker.check()
        assert isinstance(result, HealthStatus)

    def test_check_reflects_daemon_state(self, daemon):
        checker = HealthChecker(daemon, {})
        result = checker.check()
        assert result.running is True
        assert result.uptime_seconds == 42.0

    def test_check_includes_job_metrics(self, daemon):
        metrics = {"backup": _make_metrics(total=10, slow=1, missed=0, success_rate=0.9, avg=1.5, max_=3.2)}
        checker = HealthChecker(daemon, metrics)
        result = checker.check()
        assert "backup" in result.job_statuses
        job = result.job_statuses["backup"]
        assert job["total_runs"] == 10
        assert job["slow_runs"] == 1
        assert job["success_rate"] == 0.9

    def test_check_handles_none_durations(self, daemon):
        metrics = {"job1": _make_metrics(avg=None, max_=None)}
        checker = HealthChecker(daemon, metrics)
        result = checker.check()
        assert result.job_statuses["job1"]["avg_duration_seconds"] is None
        assert result.job_statuses["job1"]["max_duration_seconds"] is None

    def test_unhealthy_propagated_from_metrics(self, daemon):
        metrics = {"failing": _make_metrics(total=5, success_rate=0.0)}
        checker = HealthChecker(daemon, metrics)
        result = checker.check()
        assert result.healthy is False
