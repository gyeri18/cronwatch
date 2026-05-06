"""Tests for cronwatch.silence."""

from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.silence import SilenceManager, SilenceWindow


def _dt(offset_minutes: int = 0) -> datetime:
    """Return a UTC datetime relative to a fixed reference point."""
    base = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(minutes=offset_minutes)


# ---------------------------------------------------------------------------
# SilenceWindow
# ---------------------------------------------------------------------------

class TestSilenceWindow:
    def test_active_within_range(self):
        w = SilenceWindow("maint", start=_dt(-10), end=_dt(10))
        assert w.is_active(at=_dt(0)) is True

    def test_inactive_before_start(self):
        w = SilenceWindow("maint", start=_dt(5), end=_dt(15))
        assert w.is_active(at=_dt(0)) is False

    def test_inactive_after_end(self):
        w = SilenceWindow("maint", start=_dt(-15), end=_dt(-5))
        assert w.is_active(at=_dt(0)) is False

    def test_active_at_boundary_start(self):
        w = SilenceWindow("maint", start=_dt(0), end=_dt(10))
        assert w.is_active(at=_dt(0)) is True

    def test_active_at_boundary_end(self):
        w = SilenceWindow("maint", start=_dt(-10), end=_dt(0))
        assert w.is_active(at=_dt(0)) is True

    def test_covers_job_empty_list_means_all(self):
        w = SilenceWindow("maint", start=_dt(-1), end=_dt(1))
        assert w.covers_job("any_job") is True

    def test_covers_job_specific_match(self):
        w = SilenceWindow("maint", start=_dt(-1), end=_dt(1), jobs=["backup"])
        assert w.covers_job("backup") is True

    def test_does_not_cover_other_job(self):
        w = SilenceWindow("maint", start=_dt(-1), end=_dt(1), jobs=["backup"])
        assert w.covers_job("report") is False


# ---------------------------------------------------------------------------
# SilenceManager
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager() -> SilenceManager:
    return SilenceManager()


class TestSilenceManager:
    def test_initially_empty(self, manager):
        assert len(manager) == 0

    def test_add_increases_count(self, manager):
        manager.add(SilenceWindow("w1", start=_dt(-1), end=_dt(1)))
        assert len(manager) == 1

    def test_is_silenced_active_window(self, manager):
        manager.add(SilenceWindow("w1", start=_dt(-5), end=_dt(5)))
        assert manager.is_silenced("any", at=_dt(0)) is True

    def test_is_not_silenced_inactive_window(self, manager):
        manager.add(SilenceWindow("w1", start=_dt(10), end=_dt(20)))
        assert manager.is_silenced("any", at=_dt(0)) is False

    def test_is_not_silenced_wrong_job(self, manager):
        manager.add(SilenceWindow("w1", start=_dt(-5), end=_dt(5), jobs=["backup"]))
        assert manager.is_silenced("report", at=_dt(0)) is False

    def test_remove_existing_window(self, manager):
        manager.add(SilenceWindow("w1", start=_dt(-1), end=_dt(1)))
        removed = manager.remove("w1")
        assert removed is True
        assert len(manager) == 0

    def test_remove_nonexistent_returns_false(self, manager):
        assert manager.remove("ghost") is False

    def test_active_windows_filters_correctly(self, manager):
        manager.add(SilenceWindow("active", start=_dt(-5), end=_dt(5)))
        manager.add(SilenceWindow("future", start=_dt(10), end=_dt(20)))
        active = manager.active_windows(at=_dt(0))
        assert len(active) == 1
        assert active[0].name == "active"

    def test_multiple_windows_any_active_silences(self, manager):
        manager.add(SilenceWindow("w1", start=_dt(10), end=_dt(20)))
        manager.add(SilenceWindow("w2", start=_dt(-5), end=_dt(5)))
        assert manager.is_silenced("job", at=_dt(0)) is True
