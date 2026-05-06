"""Tests for cronwatch.config — config loading and parsing."""

from __future__ import annotations

import textwrap
import pytest

# Ensure yaml is available for tests.
pytest.importorskip("yaml")

from cronwatch.config import (
    CronwatchConfig,
    JobConfig,
    NotifierConfig,
    _parse_job,
    _parse_notifier,
    load_config,
)


# ---------------------------------------------------------------------------
# _parse_job
# ---------------------------------------------------------------------------

class TestParseJob:
    def test_minimal_job(self):
        jcfg = _parse_job({"name": "myjob", "schedule": "* * * * *"})
        assert jcfg.name == "myjob"
        assert jcfg.schedule == "* * * * *"
        assert jcfg.timeout == 300
        assert jcfg.grace == 60
        assert jcfg.tags == []

    def test_full_job(self):
        raw = {"name": "j", "schedule": "0 * * * *", "timeout": 120, "grace": 30, "tags": ["a"]}
        jcfg = _parse_job(raw)
        assert jcfg.timeout == 120
        assert jcfg.grace == 30
        assert jcfg.tags == ["a"]

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            _parse_job({"schedule": "* * * * *"})

    def test_missing_schedule_raises(self):
        with pytest.raises(ValueError, match="schedule"):
            _parse_job({"name": "j"})


# ---------------------------------------------------------------------------
# _parse_notifier
# ---------------------------------------------------------------------------

class TestParseNotifier:
    def test_log_notifier(self):
        ncfg = _parse_notifier({"kind": "log", "level": "ERROR"})
        assert ncfg.kind == "log"
        assert ncfg.level == "ERROR"

    def test_webhook_notifier(self):
        ncfg = _parse_notifier({"kind": "webhook", "url": "https://example.com"})
        assert ncfg.url == "https://example.com"

    def test_missing_kind_raises(self):
        with pytest.raises(ValueError, match="kind"):
            _parse_notifier({"url": "https://x.com"})


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_load_valid_file(self, tmp_path):
        cfg_text = textwrap.dedent("""
            jobs:
              - name: test-job
                schedule: "*/5 * * * *"
                timeout: 60
            notifiers:
              - kind: print
        """)
        cfg_file = tmp_path / "cronwatch.yaml"
        cfg_file.write_text(cfg_text)

        cfg = load_config(str(cfg_file))
        assert isinstance(cfg, CronwatchConfig)
        assert len(cfg.jobs) == 1
        assert cfg.jobs[0].name == "test-job"
        assert len(cfg.notifiers) == 1

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "missing.yaml"))

    def test_empty_file_returns_empty_config(self, tmp_path):
        cfg_file = tmp_path / "empty.yaml"
        cfg_file.write_text("")
        cfg = load_config(str(cfg_file))
        assert cfg.jobs == []
        assert cfg.notifiers == []
