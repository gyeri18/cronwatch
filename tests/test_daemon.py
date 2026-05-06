"""Tests for the Daemon class."""

import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from cronwatch.daemon import Daemon


@pytest.fixture()
def watcher():
    return MagicMock()


class TestDaemonLifecycle:
    def test_uptime_none_before_start(self, watcher):
        daemon = Daemon(watcher, poll_interval=1)
        assert daemon.uptime_seconds is None

    def test_uptime_positive_after_start(self, watcher):
        daemon = Daemon(watcher, poll_interval=60)
        daemon._start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert daemon.uptime_seconds > 0

    def test_stop_sets_running_false(self, watcher):
        daemon = Daemon(watcher, poll_interval=60)
        daemon._running = True
        daemon.stop()
        assert not daemon._running


class TestDaemonLoop:
    def test_watcher_check_called_each_tick(self, watcher):
        daemon = Daemon(watcher, poll_interval=0)
        tick_count = 0

        def fake_check(now):
            nonlocal tick_count
            tick_count += 1
            if tick_count >= 3:
                daemon.stop()

        watcher.check.side_effect = fake_check
        daemon.start()
        assert watcher.check.call_count >= 3

    def test_exception_in_check_does_not_crash_loop(self, watcher):
        daemon = Daemon(watcher, poll_interval=0)
        call_count = 0

        def flaky_check(now):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("boom")
            daemon.stop()

        watcher.check.side_effect = flaky_check
        daemon.start()  # should not raise
        assert call_count == 2

    def test_start_sets_start_time(self, watcher):
        daemon = Daemon(watcher, poll_interval=0)
        watcher.check.side_effect = lambda now: daemon.stop()
        daemon.start()
        assert daemon._start_time is not None


class TestDaemonSignals:
    def test_handle_signal_stops_daemon(self, watcher):
        daemon = Daemon(watcher, poll_interval=60)
        daemon._running = True
        daemon._handle_signal(15, None)
        assert not daemon._running
