"""Main daemon loop that ties together watcher, tracker, and alerter."""

import logging
import signal
import time
from datetime import datetime, timezone
from typing import Optional

from cronwatch.watcher import Watcher

logger = logging.getLogger(__name__)


class Daemon:
    """Runs the cronwatch monitoring loop."""

    def __init__(self, watcher: Watcher, poll_interval: int = 60) -> None:
        self._watcher = watcher
        self._poll_interval = poll_interval
        self._running = False
        self._start_time: Optional[datetime] = None

    def start(self) -> None:
        """Start the daemon loop, blocking until stopped."""
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        logger.info("cronwatch daemon started (poll_interval=%ds)", self._poll_interval)
        try:
            self._loop()
        finally:
            logger.info("cronwatch daemon stopped")

    def stop(self) -> None:
        """Request the daemon to stop after the current iteration."""
        logger.info("Stop requested")
        self._running = False

    @property
    def uptime_seconds(self) -> Optional[float]:
        if self._start_time is None:
            return None
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()

    def _loop(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc)
            logger.debug("Tick at %s", now.isoformat())
            try:
                self._watcher.check(now)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Error during watcher check")
            if self._running:
                time.sleep(self._poll_interval)

    def _handle_signal(self, signum: int, _frame) -> None:  # type: ignore[type-arg]
        logger.info("Received signal %d, stopping", signum)
        self.stop()
