"""Alert suppression rules based on job name patterns and alert kinds."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class SuppressionRule:
    """A rule that suppresses alerts matching a job pattern and/or alert kind."""

    job_pattern: str  # supports fnmatch wildcards, e.g. "backup_*"
    kinds: Optional[Set[str]] = None  # None means all kinds
    reason: str = ""

    def matches(self, job_name: str, kind: str) -> bool:
        """Return True if this rule suppresses the given job/kind combination."""
        if not fnmatch.fnmatch(job_name, self.job_pattern):
            return False
        if self.kinds is not None and kind not in self.kinds:
            return False
        return True


@dataclass
class SuppressionManager:
    """Manages a collection of suppression rules."""

    _rules: List[SuppressionRule] = field(default_factory=list)

    def add_rule(self, rule: SuppressionRule) -> None:
        """Register a suppression rule."""
        self._rules.append(rule)

    def remove_rule(self, rule: SuppressionRule) -> None:
        """Remove a previously registered rule."""
        self._rules.remove(rule)

    def is_suppressed(self, job_name: str, kind: str) -> bool:
        """Return True if any rule suppresses this job/kind pair."""
        return any(r.matches(job_name, kind) for r in self._rules)

    def matching_rules(self, job_name: str, kind: str) -> List[SuppressionRule]:
        """Return all rules that match the given job/kind pair."""
        return [r for r in self._rules if r.matches(job_name, kind)]

    @property
    def rules(self) -> List[SuppressionRule]:
        return list(self._rules)
