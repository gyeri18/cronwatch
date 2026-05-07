"""Alert aggregator: batches multiple alerts within a time window before dispatching."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatch.alerter import Alert


def _now() -> float:
    return time.monotonic()


@dataclass
class AlertBatch:
    """A collected batch of alerts ready for dispatch."""

    alerts: List[Alert]
    opened_at: float
    closed_at: float

    @property
    def size(self) -> int:
        return len(self.alerts)

    def job_names(self) -> List[str]:
        return list({a.job for a in self.alerts})


class AlertAggregator:
    """Buffers alerts and flushes them as a batch after *window_seconds* have elapsed.

    Args:
        window_seconds: How long to collect alerts before flushing.
        handler: Callable that receives an :class:`AlertBatch` when flushed.
        clock: Injectable clock function (defaults to :func:`time.monotonic`).
    """

    def __init__(
        self,
        window_seconds: float,
        handler: Callable[[AlertBatch], None],
        *,
        clock: Callable[[], float] = _now,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window = window_seconds
        self._handler = handler
        self._clock = clock
        self._buffer: List[Alert] = []
        self._window_start: Optional[float] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, alert: Alert) -> None:
        """Add *alert* to the current window, flushing first if the window expired."""
        now = self._clock()
        if self._window_start is None:
            self._window_start = now
        elif now - self._window_start >= self._window:
            self._flush(closed_at=now)
            self._window_start = now
        self._buffer.append(alert)

    def flush(self) -> None:
        """Force an immediate flush regardless of the window."""
        if self._buffer:
            self._flush(closed_at=self._clock())

    @property
    def pending(self) -> int:
        """Number of alerts currently buffered."""
        return len(self._buffer)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flush(self, closed_at: float) -> None:
        if not self._buffer:
            return
        batch = AlertBatch(
            alerts=list(self._buffer),
            opened_at=self._window_start or closed_at,
            closed_at=closed_at,
        )
        self._buffer.clear()
        self._window_start = None
        self._handler(batch)
