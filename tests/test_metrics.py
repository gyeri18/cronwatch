"""Tests for cronwatch.metrics."""
import pytest
from cronwatch.metrics import JobMetrics, MetricsCollector


# ---------------------------------------------------------------------------
# JobMetrics unit tests
# ---------------------------------------------------------------------------

class TestJobMetrics:
    def test_initial_state(self):
        m = JobMetrics(name="backup")
        assert m.run_count == 0
        assert m.miss_count == 0
        assert m.slow_count == 0
        assert m.avg_duration is None
        assert m.max_duration is None
        assert m.success_rate is None

    def test_record_run_increments_count(self):
        m = JobMetrics(name="backup")
        m.record_run(10.0)
        assert m.run_count == 1
        assert m.slow_count == 0

    def test_record_slow_run(self):
        m = JobMetrics(name="backup")
        m.record_run(30.0, slow=True)
        assert m.slow_count == 1
        assert m.run_count == 1

    def test_avg_duration_single_run(self):
        m = JobMetrics(name="backup")
        m.record_run(20.0)
        assert m.avg_duration == pytest.approx(20.0)

    def test_avg_duration_multiple_runs(self):
        m = JobMetrics(name="backup")
        for d in [10.0, 20.0, 30.0]:
            m.record_run(d)
        assert m.avg_duration == pytest.approx(20.0)

    def test_max_duration(self):
        m = JobMetrics(name="backup")
        m.record_run(5.0)
        m.record_run(50.0)
        assert m.max_duration == pytest.approx(50.0)

    def test_record_miss(self):
        m = JobMetrics(name="backup")
        m.record_miss()
        assert m.miss_count == 1
        assert m.run_count == 0

    def test_success_rate_all_good(self):
        m = JobMetrics(name="backup")
        m.record_run(5.0)
        m.record_run(6.0)
        assert m.success_rate == pytest.approx(1.0)

    def test_success_rate_with_slow(self):
        m = JobMetrics(name="backup")
        m.record_run(5.0)
        m.record_run(60.0, slow=True)
        assert m.success_rate == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# MetricsCollector integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def collector():
    return MetricsCollector()


class TestMetricsCollector:
    def test_get_returns_none_for_unknown_job(self, collector):
        assert collector.get("unknown") is None

    def test_record_run_creates_entry(self, collector):
        collector.record_run("nightly", 12.5)
        m = collector.get("nightly")
        assert m is not None
        assert m.run_count == 1

    def test_record_miss_creates_entry(self, collector):
        collector.record_miss("nightly")
        m = collector.get("nightly")
        assert m is not None
        assert m.miss_count == 1

    def test_all_metrics_returns_all_jobs(self, collector):
        collector.record_run("job_a", 1.0)
        collector.record_run("job_b", 2.0)
        assert set(collector.all_metrics().keys()) == {"job_a", "job_b"}

    def test_summary_empty(self, collector):
        assert collector.summary() == "No metrics recorded."

    def test_summary_contains_job_name(self, collector):
        collector.record_run("deploy", 8.0)
        assert "deploy" in collector.summary()

    def test_slow_flag_propagated(self, collector):
        collector.record_run("nightly", 120.0, slow=True)
        assert collector.get("nightly").slow_count == 1
