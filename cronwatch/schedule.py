"""Cron schedule parsing and next-run calculation utilities."""

import re
from datetime import datetime, timedelta
from typing import Optional


CRON_FIELDS = ["minute", "hour", "day", "month", "weekday"]


class CronSchedule:
    """Represents a parsed cron expression and provides next-run calculation."""

    def __init__(self, expression: str) -> None:
        self.expression = expression.strip()
        self._fields = self._parse(self.expression)

    def _parse(self, expression: str) -> list[set[int]]:
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression '{expression}': expected 5 fields, got {len(parts)}"
            )
        ranges = [
            (0, 59),  # minute
            (0, 23),  # hour
            (1, 31),  # day
            (1, 12),  # month
            (0, 6),   # weekday
        ]
        return [self._expand_field(part, lo, hi) for part, (lo, hi) in zip(parts, ranges)]

    def _expand_field(self, field: str, lo: int, hi: int) -> set[int]:
        values: set[int] = set()
        for token in field.split(","):
            if token == "*":
                values.update(range(lo, hi + 1))
            elif re.fullmatch(r"\*/\d+", token):
                step = int(token[2:])
                if step == 0:
                    raise ValueError("Step value cannot be zero")
                values.update(range(lo, hi + 1, step))
            elif re.fullmatch(r"\d+-\d+", token):
                a, b = map(int, token.split("-"))
                values.update(range(a, b + 1))
            elif re.fullmatch(r"\d+", token):
                values.add(int(token))
            else:
                raise ValueError(f"Unrecognised cron token: '{token}'")
        return values

    def next_run(self, after: Optional[datetime] = None) -> datetime:
        """Return the next datetime this schedule fires after *after* (default: now)."""
        dt = (after or datetime.now()).replace(second=0, microsecond=0) + timedelta(minutes=1)
        # Iterate up to 4 years to avoid infinite loops on bad schedules.
        limit = dt + timedelta(days=366 * 4)
        while dt < limit:
            if dt.month not in self._fields[3]:
                dt = dt.replace(day=1, hour=0, minute=0) + timedelta(
                    days=32 - dt.day
                )
                dt = dt.replace(day=1)
                continue
            if dt.day not in self._fields[2] or dt.weekday() not in self._fields[4]:
                dt = dt.replace(hour=0, minute=0) + timedelta(days=1)
                continue
            if dt.hour not in self._fields[1]:
                dt = dt.replace(minute=0) + timedelta(hours=1)
                continue
            if dt.minute not in self._fields[0]:
                dt += timedelta(minutes=1)
                continue
            return dt
        raise RuntimeError("Could not determine next run within 4 years")
