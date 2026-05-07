"""Tests for cronwatch.correlation."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cronwatch.alerter import Alert
from cronwatch.correlation import CorrelationEngine, Incident


def _alert(job: str = "backup", kind: str = "missed", msg: str = "late") -> Alert:
    return Alert(job_name=job, kind=kind, message=msg)


def _make_clock(start: datetime):
    state = {"t": start}

    def clock():
        return state["t"]

    def advance(seconds: float):
        state["t"] += timedelta(seconds=seconds)

    return clock, advance


class TestIncident:
    def test_is_open_initially(self):
        inc = Incident(incident_id="x", job_name="j", kind="missed")
        assert inc.is_open is True

    def test_close_sets_closed_at(self):
        ts = datetime(2024, 1, 1, 12, 0)
        inc = Incident(incident_id="x", job_name="j", kind="missed")
        inc.close(ts)
        assert inc.closed_at == ts
        assert inc.is_open is False

    def test_size_reflects_alerts(self):
        inc = Incident(incident_id="x", job_name="j", kind="missed")
        inc.add(_alert())
        inc.add(_alert())
        assert inc.size == 2

    def test_to_dict_keys(self):
        inc = Incident(incident_id="abc", job_name="j", kind="slow")
        inc.add(_alert(kind="slow"))
        d = inc.to_dict()
        assert d["incident_id"] == "abc"
        assert d["job_name"] == "j"
        assert d["kind"] == "slow"
        assert d["size"] == 1
        assert d["is_open"] is True
        assert d["closed_at"] is None


class TestCorrelationEngine:
    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            CorrelationEngine(window=timedelta(seconds=-1))

    def test_zero_window_raises(self):
        with pytest.raises(ValueError):
            CorrelationEngine(window=timedelta(0))

    def test_first_alert_opens_incident(self):
        engine = CorrelationEngine()
        inc = engine.ingest(_alert())
        assert inc.size == 1
        assert inc.is_open

    def test_second_alert_same_job_kind_appends(self):
        engine = CorrelationEngine()
        inc1 = engine.ingest(_alert())
        inc2 = engine.ingest(_alert())
        assert inc1.incident_id == inc2.incident_id
        assert inc1.size == 2

    def test_different_kind_opens_new_incident(self):
        engine = CorrelationEngine()
        inc1 = engine.ingest(_alert(kind="missed"))
        inc2 = engine.ingest(_alert(kind="slow"))
        assert inc1.incident_id != inc2.incident_id

    def test_expired_window_opens_new_incident(self):
        clock, advance = _make_clock(datetime(2024, 6, 1, 10, 0))
        engine = CorrelationEngine(window=timedelta(minutes=2), clock=clock)
        inc1 = engine.ingest(_alert())
        advance(180)  # 3 minutes — beyond window
        inc2 = engine.ingest(_alert())
        assert inc1.incident_id != inc2.incident_id

    def test_within_window_reuses_incident(self):
        clock, advance = _make_clock(datetime(2024, 6, 1, 10, 0))
        engine = CorrelationEngine(window=timedelta(minutes=5), clock=clock)
        inc1 = engine.ingest(_alert())
        advance(60)
        inc2 = engine.ingest(_alert())
        assert inc1.incident_id == inc2.incident_id

    def test_close_incident_removes_from_open(self):
        engine = CorrelationEngine()
        engine.ingest(_alert(job="backup", kind="missed"))
        closed = engine.close_incident("backup", "missed")
        assert closed is not None
        assert closed.is_open is False
        assert engine.open_incidents() == []

    def test_close_nonexistent_returns_none(self):
        engine = CorrelationEngine()
        result = engine.close_incident("ghost", "missed")
        assert result is None

    def test_open_incidents_lists_all(self):
        engine = CorrelationEngine()
        engine.ingest(_alert(job="a", kind="missed"))
        engine.ingest(_alert(job="b", kind="slow"))
        assert len(engine.open_incidents()) == 2
