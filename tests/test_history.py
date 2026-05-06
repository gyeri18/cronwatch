"""Tests for cronwatch.history module."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from cronwatch.history import HistoryEntry, JobHistory


def _entry(name="backup", status="success", duration=5.0):
    return HistoryEntry(
        job_name=name,
        started_at="2024-01-01T00:00:00",
        finished_at="2024-01-01T00:00:05",
        duration_seconds=duration,
        exit_code=0,
        status=status,
    )


@pytest.fixture
def tmp_path_file(tmp_path):
    return str(tmp_path / "history.json")


class TestHistoryEntry:
    def test_to_dict_roundtrip(self):
        e = _entry()
        assert HistoryEntry.from_dict(e.to_dict()) == e

    def test_from_dict_creates_entry(self):
        data = _entry().to_dict()
        e = HistoryEntry.from_dict(data)
        assert e.job_name == "backup"
        assert e.status == "success"


class TestJobHistory:
    def test_record_persists_to_file(self, tmp_path_file):
        h = JobHistory(tmp_path_file)
        h.record(_entry())
        assert Path(tmp_path_file).exists()
        with open(tmp_path_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["job_name"] == "backup"

    def test_load_on_init(self, tmp_path_file):
        h = JobHistory(tmp_path_file)
        h.record(_entry())
        h2 = JobHistory(tmp_path_file)
        assert len(h2) == 1

    def test_get_job_filters_by_name(self, tmp_path_file):
        h = JobHistory(tmp_path_file)
        h.record(_entry(name="backup"))
        h.record(_entry(name="cleanup"))
        results = h.get_job("backup")
        assert len(results) == 1
        assert results[0].job_name == "backup"

    def test_get_recent_returns_limit(self, tmp_path_file):
        h = JobHistory(tmp_path_file)
        for _ in range(10):
            h.record(_entry())
        assert len(h.get_recent(limit=5)) == 5

    def test_max_entries_cap(self, tmp_path_file):
        h = JobHistory(tmp_path_file, max_entries=3)
        for _ in range(5):
            h.record(_entry())
        assert len(h) == 3

    def test_clear_empties_history(self, tmp_path_file):
        h = JobHistory(tmp_path_file)
        h.record(_entry())
        h.clear()
        assert len(h) == 0

    def test_missing_file_starts_empty(self, tmp_path_file):
        h = JobHistory(tmp_path_file)
        assert len(h) == 0
