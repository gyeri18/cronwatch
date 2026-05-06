"""Rate limiter for alert notifications — prevents alert storms."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional


def _now() -> float:
    return time.monotonic()


@dataclass
class _Bucket:
    tokens: float
    last_refill: float = field(default_factory=_now)


class RateLimiter:
    """Token-bucket rate limiter keyed by (job_name, alert_kind).

    Each bucket starts full.  One token is consumed per alert.  Tokens
    refill at ``rate`` per second up to ``capacity``.
    """

    def __init__(self, capacity: int = 5, rate: float = 1.0) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        if rate <= 0:
            raise ValueError("rate must be > 0")
        self.capacity = capacity
        self.rate = rate  # tokens per second
        self._buckets: Dict[tuple, _Bucket] = defaultdict(
            lambda: _Bucket(tokens=float(capacity))
        )

    def _refill(self, bucket: _Bucket) -> None:
        now = _now()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(
            float(self.capacity),
            bucket.tokens + elapsed * self.rate,
        )
        bucket.last_refill = now

    def allow(self, job: str, kind: str) -> bool:
        """Return True and consume a token if the alert is allowed."""
        key = (job, kind)
        bucket = self._buckets[key]
        self._refill(bucket)
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True
        return False

    def available_tokens(self, job: str, kind: str) -> float:
        """Return current token count (after refill) without consuming."""
        key = (job, kind)
        bucket = self._buckets[key]
        self._refill(bucket)
        return bucket.tokens

    def reset(self, job: Optional[str] = None, kind: Optional[str] = None) -> None:
        """Reset buckets.  Passing both resets a single key; passing neither resets all."""
        if job is not None and kind is not None:
            self._buckets.pop((job, kind), None)
        else:
            self._buckets.clear()
