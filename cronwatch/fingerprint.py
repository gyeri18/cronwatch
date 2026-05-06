"""Alert fingerprinting — generate stable keys for deduplication and grouping."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AlertFingerprint:
    """Immutable fingerprint derived from an alert's core attributes."""

    job: str
    kind: str
    digest: str  # hex SHA-256 of canonical fields

    def __str__(self) -> str:
        return f"{self.job}:{self.kind}:{self.digest[:12]}"


def _canonical(job: str, kind: str, extra: dict[str, Any]) -> bytes:
    """Return a stable, sorted JSON encoding of the alert's identifying fields."""
    payload = {"job": job, "kind": kind, **{k: extra[k] for k in sorted(extra)}}
    return json.dumps(payload, sort_keys=True, default=str).encode()


def compute_fingerprint(
    job: str,
    kind: str,
    extra: dict[str, Any] | None = None,
) -> AlertFingerprint:
    """Compute a stable fingerprint for the given alert attributes.

    Parameters
    ----------
    job:   Name of the cron job.
    kind:  Alert category (e.g. ``"missed"``, ``"slow"``).
    extra: Optional mapping of additional fields included in the digest.
           Only *stable* values (not timestamps) should be passed here.
    """
    data = _canonical(job, kind, extra or {})
    digest = hashlib.sha256(data).hexdigest()
    return AlertFingerprint(job=job, kind=kind, digest=digest)


@dataclass
class FingerprintRegistry:
    """Tracks which fingerprints have been seen and how many times."""

    _counts: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    def seen(self, fp: AlertFingerprint) -> bool:
        """Return ``True`` if this fingerprint has been recorded before."""
        return str(fp) in self._counts

    def record(self, fp: AlertFingerprint) -> int:
        """Record *fp* and return the new total occurrence count."""
        key = str(fp)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def count(self, fp: AlertFingerprint) -> int:
        """Return how many times *fp* has been recorded (0 if never)."""
        return self._counts.get(str(fp), 0)

    def clear(self, fp: AlertFingerprint) -> None:
        """Remove *fp* from the registry (e.g. after a job recovers)."""
        self._counts.pop(str(fp), None)

    def clear_all(self) -> None:
        """Reset the entire registry."""
        self._counts.clear()
