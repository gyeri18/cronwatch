"""Tests for cronwatch.builder — wiring config into a live Watcher."""

from __future__ import annotations

import pytest

from cronwatch.builder import _build_handler, build_watcher
from cronwatch.config import CronwatchConfig, JobConfig, NotifierConfig
from cronwatch.notifiers import WebhookNotifier, log_handler, print_handler
from cronwatch.watcher import Watcher


class TestBuildHandler:
    def test_print_kind(self):
        ncfg = NotifierConfig(kind="print")
        assert _build_handler(ncfg) is print_handler

    def test_log_kind(self):
        ncfg = NotifierConfig(kind="log")
        assert _build_handler(ncfg) is log_handler

    def test_webhook_kind(self):
        ncfg = NotifierConfig(kind="webhook", url="https://example.com/hook")
        handler = _build_handler(ncfg)
        assert isinstance(handler, WebhookNotifier)

    def test_webhook_without_url_raises(self):
        ncfg = NotifierConfig(kind="webhook")
        with pytest.raises(ValueError, match="url"):
            _build_handler(ncfg)

    def test_unknown_kind_raises(self):
        ncfg = NotifierConfig(kind="sms")
        with pytest.raises(ValueError, match="Unknown notifier kind"):
            _build_handler(ncfg)


class TestBuildWatcher:
    def _make_cfg(self, jobs=None, notifiers=None) -> CronwatchConfig:
        return CronwatchConfig(
            jobs=jobs or [],
            notifiers=notifiers or [],
        )

    def test_returns_watcher_instance(self):
        cfg = self._make_cfg()
        w = build_watcher(cfg)
        assert isinstance(w, Watcher)

    def test_jobs_are_registered(self):
        jobs = [
            JobConfig(name="job-a", schedule="* * * * *"),
            JobConfig(name="job-b", schedule="0 * * * *"),
        ]
        cfg = self._make_cfg(jobs=jobs)
        w = build_watcher(cfg)
        assert "job-a" in w.jobs
        assert "job-b" in w.jobs

    def test_fallback_print_handler_when_no_notifiers(self):
        cfg = self._make_cfg()
        w = build_watcher(cfg)
        # Alerter should have exactly one handler (print_handler fallback)
        assert len(w.alerter.handlers) == 1
        assert w.alerter.handlers[0] is print_handler

    def test_configured_notifier_is_used(self):
        cfg = self._make_cfg(notifiers=[NotifierConfig(kind="log")])
        w = build_watcher(cfg)
        assert len(w.alerter.handlers) == 1
        assert w.alerter.handlers[0] is log_handler
