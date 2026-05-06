"""Tests for cronwatch.deduplicator."""

from __future__ import annotations

import pytest

from cronwatch.alerter import Alert
from cronwatch.deduplicator import Deduplicator, _alert_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _alert(kind: str = "missed", job: str = "backup", msg: str = "overdue") -> Alert:
    return Alert(kind=kind, job_name=job, message=msg)


def _make_clock(start: float = 0.0):
    """Returns a mutable clock and a setter."""
    state = [start]

    def clock() -> float:
        return state[0]

    def advance(seconds: float) -> None:
        state[0] += seconds

    return clock, advance


# ---------------------------------------------------------------------------
# _alert_key
# ---------------------------------------------------------------------------

class TestAlertKey:
    def test_same_alert_same_key(self):
        a = _alert()
        assert _alert_key(a) == _alert_key(a)

    def test_different_kind_different_key(self):
        assert _alert_key(_alert(kind="missed")) != _alert_key(_alert(kind="slow"))

    def test_different_job_different_key(self):
        assert _alert_key(_alert(job="a")) != _alert_key(_alert(job="b"))

    def test_different_message_different_key(self):
        assert _alert_key(_alert(msg="x")) != _alert_key(_alert(msg="y"))


# ---------------------------------------------------------------------------
# Deduplicator
# ---------------------------------------------------------------------------

class TestDeduplicatorInit:
    def test_negative_cooldown_raises(self):
        with pytest.raises(ValueError):
            Deduplicator(handler=lambda a: None, cooldown=-1)

    def test_zero_cooldown_accepted(self):
        d = Deduplicator(handler=lambda a: None, cooldown=0)
        assert d is not None


class TestDeduplicatorSend:
    def setup_method(self):
        self.received: list[Alert] = []
        self.clock, self.advance = _make_clock()
        self.ded = Deduplicator(
            handler=self.received.append,
            cooldown=60.0,
            clock=self.clock,
        )

    def test_first_send_forwarded(self):
        a = _alert()
        assert self.ded.send(a) is True
        assert len(self.received) == 1

    def test_duplicate_within_cooldown_suppressed(self):
        a = _alert()
        self.ded.send(a)
        self.advance(30)
        assert self.ded.send(a) is False
        assert len(self.received) == 1

    def test_duplicate_after_cooldown_forwarded(self):
        a = _alert()
        self.ded.send(a)
        self.advance(61)
        assert self.ded.send(a) is True
        assert len(self.received) == 2

    def test_different_alerts_both_forwarded(self):
        self.ded.send(_alert(kind="missed"))
        self.ded.send(_alert(kind="slow"))
        assert len(self.received) == 2

    def test_suppressed_count_increments(self):
        a = _alert()
        self.ded.send(a)
        self.advance(10)
        self.ded.send(a)
        self.advance(10)
        self.ded.send(a)
        assert self.ded.suppressed_count(a) == 2

    def test_suppressed_count_zero_for_unseen(self):
        assert self.ded.suppressed_count(_alert()) == 0

    def test_reset_specific_alert_clears_state(self):
        a = _alert()
        self.ded.send(a)
        self.ded.reset(a)
        assert self.ded.send(a) is True
        assert len(self.received) == 2

    def test_reset_all_clears_all_state(self):
        self.ded.send(_alert(kind="missed"))
        self.ded.send(_alert(kind="slow"))
        self.ded.reset()
        self.ded.send(_alert(kind="missed"))
        self.ded.send(_alert(kind="slow"))
        assert len(self.received) == 4
