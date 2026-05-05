"""Unit tests for cronwatch.schedule."""

import pytest
from datetime import datetime

from cronwatch.schedule import CronSchedule


def dt(year=2024, month=1, day=1, hour=0, minute=0):
    return datetime(year, month, day, hour, minute)


class TestCronScheduleParsing:
    def test_valid_expression_parses(self):
        s = CronSchedule("0 9 * * 1")
        assert s.expression == "0 9 * * 1"

    def test_too_few_fields_raises(self):
        with pytest.raises(ValueError, match="expected 5 fields"):
            CronSchedule("* * * *")

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Unrecognised cron token"):
            CronSchedule("? * * * *")

    def test_zero_step_raises(self):
        with pytest.raises(ValueError, match="Step value cannot be zero"):
            CronSchedule("*/0 * * * *")


class TestNextRun:
    def test_every_minute(self):
        s = CronSchedule("* * * * *")
        after = dt(minute=30)
        nxt = s.next_run(after)
        assert nxt == dt(minute=31)

    def test_top_of_hour(self):
        s = CronSchedule("0 * * * *")
        after = dt(hour=10, minute=5)
        nxt = s.next_run(after)
        assert nxt == dt(hour=11, minute=0)

    def test_daily_at_midnight(self):
        s = CronSchedule("0 0 * * *")
        after = dt(hour=12, minute=0)
        nxt = s.next_run(after)
        assert nxt == dt(hour=0, minute=0) + __import__("datetime").timedelta(days=1)

    def test_specific_day_of_week(self):
        # 0 9 * * 1 => 09:00 every Monday
        s = CronSchedule("0 9 * * 1")
        # 2024-01-01 is a Monday
        after = dt(year=2024, month=1, day=1, hour=9, minute=0)
        nxt = s.next_run(after)
        assert nxt.weekday() == 0  # Monday
        assert nxt.hour == 9 and nxt.minute == 0

    def test_step_expression(self):
        s = CronSchedule("*/15 * * * *")
        after = dt(minute=0)
        nxt = s.next_run(after)
        assert nxt.minute == 15

    def test_range_expression(self):
        s = CronSchedule("0 9-11 * * *")
        after = dt(hour=9, minute=0)
        nxt = s.next_run(after)
        assert nxt.hour == 10 and nxt.minute == 0

    def test_list_expression(self):
        s = CronSchedule("0 8,12,18 * * *")
        after = dt(hour=8, minute=0)
        nxt = s.next_run(after)
        assert nxt.hour == 12

    def test_next_run_skips_past_midnight(self):
        s = CronSchedule("0 0 * * *")
        after = dt(hour=23, minute=59)
        nxt = s.next_run(after)
        assert nxt.day == after.day + 1
        assert nxt.hour == 0 and nxt.minute == 0
