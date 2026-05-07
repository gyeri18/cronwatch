"""Tests for cronwatch/audit.py — AuditEntry and AuditLog."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cronwatch.alerter import Alert
from cronwatch.audit import AuditEntry, AuditLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _alert(job: str = "backup", kind: str = "missed") -> Alert:
    return Alert(job=job, kind=kind, message=f"{kind} alert for {job}")


# ---------------------------------------------------------------------------
# AuditEntry tests
# ---------------------------------------------------------------------------


class TestAuditEntry:
    def test_to_dict_roundtrip(self):
        alert = _alert()
        entry = AuditEntry(timestamp=FIXED_TS, alert=alert, handler="log_handler")
        d = entry.to_dict()
        restored = AuditEntry.from_dict(d)
        assert restored.handler == entry.handler
        assert restored.alert.job == entry.alert.job
        assert restored.alert.kind == entry.alert.kind
        assert restored.timestamp == entry.timestamp

    def test_to_dict_has_iso_timestamp(self):
        alert = _alert()
        entry = AuditEntry(timestamp=FIXED_TS, alert=alert, handler="print_handler")
        d = entry.to_dict()
        assert d["timestamp"] == "2024-06-01T12:00:00+00:00"

    def test_to_dict_contains_handler(self):
        alert = _alert()
        entry = AuditEntry(timestamp=FIXED_TS, alert=alert, handler="webhook")
        assert entry.to_dict()["handler"] == "webhook"

    def test_to_dict_contains_job_and_kind(self):
        alert = _alert(job="deploy", kind="slow")
        entry = AuditEntry(timestamp=FIXED_TS, alert=alert, handler="log_handler")
        d = entry.to_dict()
        assert d["job"] == "deploy"
        assert d["kind"] == "slow"

    def test_from_dict_creates_entry(self):
        data = {
            "timestamp": "2024-06-01T12:00:00+00:00",
            "job": "backup",
            "kind": "missed",
            "message": "missed alert for backup",
            "handler": "log_handler",
        }
        entry = AuditEntry.from_dict(data)
        assert entry.alert.job == "backup"
        assert entry.alert.kind == "missed"
        assert entry.handler == "log_handler"
        assert entry.timestamp == FIXED_TS


# ---------------------------------------------------------------------------
# AuditLog tests
# ---------------------------------------------------------------------------


class TestAuditLog:
    def test_record_appends_entry(self):
        log = AuditLog()
        alert = _alert()
        with patch("cronwatch.audit._utcnow", return_value=FIXED_TS):
            log.record(alert=alert, handler="log_handler")
        assert len(log) == 1

    def test_record_multiple_entries(self):
        log = AuditLog()
        with patch("cronwatch.audit._utcnow", return_value=FIXED_TS):
            log.record(alert=_alert("job1"), handler="h1")
            log.record(alert=_alert("job2"), handler="h2")
        assert len(log) == 2

    def test_entries_returns_copy(self):
        log = AuditLog()
        with patch("cronwatch.audit._utcnow", return_value=FIXED_TS):
            log.record(alert=_alert(), handler="log_handler")
        entries = log.entries()
        entries.clear()
        assert len(log) == 1

    def test_filter_by_job(self):
        log = AuditLog()
        with patch("cronwatch.audit._utcnow", return_value=FIXED_TS):
            log.record(alert=_alert("backup"), handler="h")
            log.record(alert=_alert("deploy"), handler="h")
        results = log.filter(job="backup")
        assert len(results) == 1
        assert results[0].alert.job == "backup"

    def test_filter_by_kind(self):
        log = AuditLog()
        with patch("cronwatch.audit._utcnow", return_value=FIXED_TS):
            log.record(alert=_alert(kind="missed"), handler="h")
            log.record(alert=_alert(kind="slow"), handler="h")
        results = log.filter(kind="slow")
        assert len(results) == 1
        assert results[0].alert.kind == "slow"

    def test_to_jsonable_is_list_of_dicts(self):
        log = AuditLog()
        with patch("cronwatch.audit._utcnow", return_value=FIXED_TS):
            log.record(alert=_alert(), handler="log_handler")
        data = log.to_jsonable()
        assert isinstance(data, list)
        assert isinstance(data[0], dict)
        # Verify it is JSON-serialisable
        json.dumps(data)

    def test_clear_empties_log(self):
        log = AuditLog()
        with patch("cronwatch.audit._utcnow", return_value=FIXED_TS):
            log.record(alert=_alert(), handler="log_handler")
        log.clear()
        assert len(log) == 0

    def test_max_size_evicts_oldest(self):
        log = AuditLog(max_size=2)
        with patch("cronwatch.audit._utcnow", return_value=FIXED_TS):
            log.record(alert=_alert("a"), handler="h")
            log.record(alert=_alert("b"), handler="h")
            log.record(alert=_alert("c"), handler="h")
        assert len(log) == 2
        jobs = [e.alert.job for e in log.entries()]
        assert "a" not in jobs
        assert "b" in jobs
        assert "c" in jobs
