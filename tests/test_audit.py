"""Tests for cronwatch.audit and cronwatch.alerter_audited."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.alerter import Alert, Alerter
from cronwatch.alerter_audited import AuditedAlerter
from cronwatch.audit import AuditEntry, AuditLog

_T0 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _alert(job="backup", kind="missed", message="Job missed", extra=None):
    return Alert(job=job, kind=kind, message=message, extra=extra or {})


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------

class TestAuditEntry:
    def test_to_dict_roundtrip(self):
        entry = AuditEntry(
            timestamp=_T0, job="backup", kind="missed",
            message="Job missed", extra={"threshold": 5}
        )
        restored = AuditEntry.from_dict(entry.to_dict())
        assert restored.job == entry.job
        assert restored.kind == entry.kind
        assert restored.message == entry.message
        assert restored.extra == entry.extra
        assert restored.timestamp == entry.timestamp

    def test_to_dict_has_iso_timestamp(self):
        entry = AuditEntry(timestamp=_T0, job="j", kind="k", message="m")
        assert entry.to_dict()["timestamp"] == _T0.isoformat()


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class TestAuditLog:
    def test_record_stores_entry(self):
        log = AuditLog()
        alert = _alert()
        log.record(alert, clock=lambda: _T0)
        entries = log.entries()
        assert len(entries) == 1
        assert entries[0].job == "backup"
        assert entries[0].kind == "missed"

    def test_filter_by_job(self):
        log = AuditLog()
        log.record(_alert(job="backup"), clock=lambda: _T0)
        log.record(_alert(job="sync"), clock=lambda: _T0)
        assert len(log.entries(job="backup")) == 1
        assert len(log.entries(job="sync")) == 1

    def test_max_entries_respected(self):
        log = AuditLog(max_entries=3)
        for _ in range(5):
            log.record(_alert(), clock=lambda: _T0)
        assert len(log.entries()) == 3

    def test_clear_removes_all(self):
        log = AuditLog()
        log.record(_alert(), clock=lambda: _T0)
        log.clear()
        assert log.entries() == []

    def test_persists_to_file(self, tmp_path):
        p = tmp_path / "audit.jsonl"
        log = AuditLog(path=p)
        log.record(_alert(), clock=lambda: _T0)
        lines = p.read_text().strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["job"] == "backup"

    def test_loads_existing_file(self, tmp_path):
        p = tmp_path / "audit.jsonl"
        entry = AuditEntry(timestamp=_T0, job="x", kind="slow", message="slow")
        p.write_text(json.dumps(entry.to_dict()) + "\n")
        log = AuditLog(path=p)
        assert len(log.entries()) == 1
        assert log.entries()[0].job == "x"


# ---------------------------------------------------------------------------
# AuditedAlerter
# ---------------------------------------------------------------------------

class TestAuditedAlerter:
    def test_send_records_in_audit_log(self):
        base = Alerter()
        log = AuditLog()
        audited = AuditedAlerter(base, log)
        audited.send(_alert())
        assert len(log.entries()) == 1

    def test_send_dispatches_to_handlers(self):
        received: list = []
        base = Alerter()
        base.add_handler(received.append)
        log = AuditLog()
        audited = AuditedAlerter(base, log)
        audited.send(_alert())
        assert len(received) == 1

    def test_add_handler_delegates(self):
        received: list = []
        base = Alerter()
        log = AuditLog()
        audited = AuditedAlerter(base, log)
        audited.add_handler(received.append)
        audited.send(_alert())
        assert len(received) == 1

    def test_audit_log_property(self):
        log = AuditLog()
        audited = AuditedAlerter(Alerter(), log)
        assert audited.audit_log is log
