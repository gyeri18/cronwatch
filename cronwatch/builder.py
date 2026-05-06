"""Build a ready-to-run Watcher from a CronwatchConfig."""

from __future__ import annotations

from cronwatch.alerter import Alerter
from cronwatch.config import CronwatchConfig, NotifierConfig
from cronwatch.notifiers import WebhookNotifier, log_handler, print_handler
from cronwatch.watcher import Watcher


def _build_handler(ncfg: NotifierConfig):
    """Return a callable notifier from a NotifierConfig."""
    kind = ncfg.kind.lower()
    if kind == "print":
        return print_handler
    if kind == "log":
        return log_handler
    if kind == "webhook":
        if not ncfg.url:
            raise ValueError("Webhook notifier requires a 'url' field.")
        return WebhookNotifier(ncfg.url)
    raise ValueError(f"Unknown notifier kind: '{ncfg.kind}'")


def build_watcher(cfg: CronwatchConfig) -> Watcher:
    """Construct an Alerter and Watcher wired together from *cfg*."""
    alerter = Alerter()

    for ncfg in cfg.notifiers:
        handler = _build_handler(ncfg)
        alerter.add_handler(handler)

    # Fall back to print_handler when no notifiers are configured.
    if not cfg.notifiers:
        alerter.add_handler(print_handler)

    watcher = Watcher(alerter=alerter)

    for jcfg in cfg.jobs:
        watcher.register(
            name=jcfg.name,
            expression=jcfg.schedule,
            timeout=jcfg.timeout,
            grace=jcfg.grace,
        )

    return watcher
