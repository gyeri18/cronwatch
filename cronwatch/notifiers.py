"""Built-in alert handler implementations (log, print, webhook)."""

import json
import logging
import urllib.request
from typing import Optional

from cronwatch.alerter import Alert

logger = logging.getLogger(__name__)


def log_handler(alert: Alert) -> None:
    """Write alert to the Python logging system."""
    level = {
        "missed": logging.WARNING,
        "slow": logging.WARNING,
        "failed": logging.ERROR,
    }.get(alert.kind, logging.INFO)
    logger.log(level, str(alert))


def print_handler(alert: Alert) -> None:
    """Print alert to stdout."""
    print(str(alert))


class WebhookNotifier:
    """POST alert details as JSON to a webhook URL (e.g. Slack, Teams)."""

    def __init__(self, url: str, timeout: int = 5) -> None:
        self.url = url
        self.timeout = timeout

    def __call__(self, alert: Alert) -> None:
        payload = json.dumps(
            {
                "job": alert.job_name,
                "kind": alert.kind,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
            }
        ).encode()
        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout):
                pass
        except Exception as exc:  # noqa: BLE001
            logger.error("Webhook delivery failed for %s: %s", self.url, exc)


def make_notifier(
    kind: str,
    webhook_url: Optional[str] = None,
):
    """Factory that returns a handler callable by name.

    Supported kinds: 'log', 'print', 'webhook'.
    """
    if kind == "log":
        return log_handler
    if kind == "print":
        return print_handler
    if kind == "webhook":
        if not webhook_url:
            raise ValueError("webhook_url is required for webhook notifier")
        return WebhookNotifier(webhook_url)
    raise ValueError(f"Unknown notifier kind: {kind!r}")
