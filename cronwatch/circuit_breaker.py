"""Circuit breaker to stop alerting when a notifier is repeatedly failing."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


def _now() -> float:
    return time.monotonic()


class State(Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # blocking calls
    HALF_OPEN = "half_open"  # testing recovery


@dataclass
class CircuitBreaker:
    """Tracks consecutive failures and opens the circuit after a threshold.

    Args:
        failure_threshold: number of consecutive failures before opening.
        recovery_timeout: seconds to wait before moving to HALF_OPEN.
        name: optional label for logging / repr.
    """

    failure_threshold: int = 3
    recovery_timeout: float = 60.0
    name: str = "default"

    _state: State = field(default=State.CLOSED, init=False, repr=False)
    _failures: int = field(default=0, init=False, repr=False)
    _opened_at: Optional[float] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")

    @property
    def state(self) -> State:
        if self._state is State.OPEN:
            if self._opened_at is not None and _now() - self._opened_at >= self.recovery_timeout:
                self._state = State.HALF_OPEN
        return self._state

    @property
    def seconds_until_retry(self) -> Optional[float]:
        """Return seconds remaining before the breaker moves to HALF_OPEN.

        Returns ``None`` when the circuit is not OPEN or the timer has already
        elapsed (i.e. the transition to HALF_OPEN will happen on the next
        :pymeth:`state` access).
        """
        if self._state is not State.OPEN or self._opened_at is None:
            return None
        remaining = self.recovery_timeout - (_now() - self._opened_at)
        return max(remaining, 0.0) if remaining > 0 else None

    def allow_request(self) -> bool:
        """Return True if the caller is permitted to attempt the operation."""
        return self.state in (State.CLOSED, State.HALF_OPEN)

    def record_success(self) -> None:
        """Call after a successful operation to reset failure count."""
        self._failures = 0
        self._opened_at = None
        self._state = State.CLOSED

    def record_failure(self) -> None:
        """Call after a failed operation; may open the circuit."""
        self._failures += 1
        if self._state is State.HALF_OPEN or self._failures >= self.failure_threshold:
            self._state = State.OPEN
            self._opened_at = _now()

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED state."""
        self._failures = 0
        self._opened_at = None
        self._state = State.CLOSED

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name!r}, state={self.state.value}, "
            f"failures={self._failures}/{self.failure_threshold})"
        )
