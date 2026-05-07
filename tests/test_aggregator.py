"""Tests for cronwatch.aggregator."""

from __future__ import annotations

from typing import List

import pytest

from cronwatch.aggregator import AlertAggregator, AlertBatch
from cronwatch.alerter import Alert


def _alert(job: str = "myjob", kind: str = "missed") -> Alert:
    return Alert(job=job, kind=kind, message="test")


def _make_clock(start: float = 0.0):
    """Returns a mutable clock and an advance helper."""
    state = {"t": start}

    def clock() -> float:
        return state["t"]

    def advance(seconds: float) -> None:
        state["t"] += seconds

    return clock, advance


@pytest.fixture()
def batches() -> List[AlertBatch]:
    return []


@pytest.fixture()
def clock_pair():
    return _make_clock()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestAggregatorInit:
    def test_positive_window_accepted(self):
        agg = AlertAggregator(window_seconds=5.0, handler=lambda b: None)
        assert agg.pending == 0

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="positive"):
            AlertAggregator(window_seconds=0, handler=lambda b: None)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            AlertAggregator(window_seconds=-1, handler=lambda b: None)


# ---------------------------------------------------------------------------
# Buffering behaviour
# ---------------------------------------------------------------------------

class TestAggregatorBuffering:
    def test_pending_increments_on_add(self, batches, clock_pair):
        clock, _ = clock_pair
        agg = AlertAggregator(5.0, batches.append, clock=clock)
        agg.add(_alert())
        assert agg.pending == 1

    def test_no_flush_within_window(self, batches, clock_pair):
        clock, advance = clock_pair
        agg = AlertAggregator(10.0, batches.append, clock=clock)
        agg.add(_alert())
        advance(4.9)
        agg.add(_alert())
        assert len(batches) == 0
        assert agg.pending == 2

    def test_flush_triggered_after_window(self, batches, clock_pair):
        clock, advance = clock_pair
        agg = AlertAggregator(5.0, batches.append, clock=clock)
        agg.add(_alert())
        advance(5.0)
        agg.add(_alert())  # this add triggers flush of previous window
        assert len(batches) == 1
        assert batches[0].size == 1

    def test_force_flush_dispatches_batch(self, batches, clock_pair):
        clock, _ = clock_pair
        agg = AlertAggregator(30.0, batches.append, clock=clock)
        agg.add(_alert("job1"))
        agg.add(_alert("job2"))
        agg.flush()
        assert len(batches) == 1
        assert batches[0].size == 2
        assert agg.pending == 0

    def test_force_flush_empty_buffer_is_noop(self, batches, clock_pair):
        clock, _ = clock_pair
        agg = AlertAggregator(5.0, batches.append, clock=clock)
        agg.flush()
        assert batches == []

    def test_batch_job_names(self, batches, clock_pair):
        clock, _ = clock_pair
        agg = AlertAggregator(5.0, batches.append, clock=clock)
        agg.add(_alert("alpha"))
        agg.add(_alert("beta"))
        agg.add(_alert("alpha"))
        agg.flush()
        assert sorted(batches[0].job_names()) == ["alpha", "beta"]

    def test_pending_resets_after_flush(self, batches, clock_pair):
        clock, _ = clock_pair
        agg = AlertAggregator(5.0, batches.append, clock=clock)
        agg.add(_alert())
        agg.flush()
        assert agg.pending == 0
