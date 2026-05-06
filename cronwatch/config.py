"""Configuration loading and validation for cronwatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class NotifierConfig:
    kind: str
    url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobConfig:
    name: str
    schedule: str
    timeout: int
    grace: int = 0


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig]
    notifiers: List[NotifierConfig]

    @classmethod
    def from_file(cls, path: Path) -> "CronwatchConfig":
        with path.open() as fh:
            data = yaml.safe_load(fh)
        return cls(
            jobs=[_parse_job(j) for j in data.get("jobs", [])],
            notifiers=[_parse_notifier(n) for n in data.get("notifiers", [])],
        )


def _parse_job(data: Dict[str, Any]) -> JobConfig:
    if "name" not in data:
        raise ValueError("Job entry missing required field 'name'")
    if "schedule" not in data:
        raise ValueError("Job entry missing required field 'schedule'")
    if "timeout" not in data:
        raise ValueError("Job entry missing required field 'timeout'")
    return JobConfig(
        name=data["name"],
        schedule=data["schedule"],
        timeout=int(data["timeout"]),
        grace=int(data.get("grace", 0)),
    )


def _parse_notifier(data: Dict[str, Any]) -> NotifierConfig:
    if "kind" not in data:
        raise ValueError("Notifier entry missing required field 'kind'")
    known = {"url"}
    extra = {k: v for k, v in data.items() if k not in known | {"kind"}}
    return NotifierConfig(
        kind=data["kind"],
        url=data.get("url"),
        extra=extra,
    )
