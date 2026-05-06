"""Configuration loader for cronwatch.

Supports YAML config files defining jobs to watch, alert thresholds,
and notifier settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass
class JobConfig:
    name: str
    schedule: str
    timeout: int = 300          # seconds before a running job is considered slow
    grace: int = 60             # seconds after expected start before "missed" alert
    tags: list[str] = field(default_factory=list)


@dataclass
class NotifierConfig:
    kind: str                   # "log", "print", or "webhook"
    url: str | None = None      # for webhook
    level: str = "WARNING"      # for log notifier


@dataclass
class CronwatchConfig:
    jobs: list[JobConfig] = field(default_factory=list)
    notifiers: list[NotifierConfig] = field(default_factory=list)


def _parse_job(raw: dict[str, Any]) -> JobConfig:
    if "name" not in raw:
        raise ValueError("Each job entry must have a 'name' field.")
    if "schedule" not in raw:
        raise ValueError(f"Job '{raw['name']}' is missing a 'schedule' field.")
    return JobConfig(
        name=raw["name"],
        schedule=raw["schedule"],
        timeout=int(raw.get("timeout", 300)),
        grace=int(raw.get("grace", 60)),
        tags=list(raw.get("tags", [])),
    )


def _parse_notifier(raw: dict[str, Any]) -> NotifierConfig:
    if "kind" not in raw:
        raise ValueError("Each notifier entry must have a 'kind' field.")
    return NotifierConfig(
        kind=raw["kind"],
        url=raw.get("url"),
        level=raw.get("level", "WARNING"),
    )


def load_config(path: str) -> CronwatchConfig:
    """Load a YAML config file and return a CronwatchConfig."""
    if yaml is None:
        raise RuntimeError("PyYAML is required to load config files. Install it with: pip install pyyaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh) or {}
    jobs = [_parse_job(j) for j in raw.get("jobs", [])]
    notifiers = [_parse_notifier(n) for n in raw.get("notifiers", [])]
    return CronwatchConfig(jobs=jobs, notifiers=notifiers)
