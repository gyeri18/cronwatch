"""Build a configured :class:`Watcher` from a :class:`CronwatchConfig`."""

from __future__ import annotations

from cronwatch.alerter import Alerter
from cronwatch.config import CronwatchConfig, NotifierConfig
from cronwatch.notifiers import log_handler, print_handler, WebhookNotifier
from cronwatch.throttle import AlertThrottle
from cronwatch.watcher import Watcher


def _build_handler(cfg: NotifierConfig):
    """Instantiate a notifier callable from *cfg*."""
    kind = cfg.kind.lower()
    if kind == "print":
        return print_handler
    if kind == "log":
        return log_handler
    if kind == "webhook":
        if not cfg.url:
            raise ValueError("Webhook notifier requires a 'url' field")
        return WebhookNotifier(url=cfg.url, timeout=cfg.timeout)
    raise ValueError(f"Unknown notifier kind: {cfg.kind!r}")


def build_watcher(
    config: CronwatchConfig,
    throttle: AlertThrottle | None = None,
) -> Watcher:
    """Construct a fully-wired :class:`Watcher` from *config*.

    If *throttle* is provided it will be attached to the :class:`Alerter`
    so that repeated alerts are suppressed according to the throttle rules.
    If *config* specifies a ``throttle_interval_seconds`` value a default
    :class:`AlertThrottle` is created automatically when *throttle* is
    ``None``.
    """
    if throttle is None and getattr(config, "throttle_interval_seconds", None):
        throttle = AlertThrottle(
            default_interval_seconds=config.throttle_interval_seconds
        )

    alerter = Alerter(throttle=throttle)

    for notifier_cfg in config.notifiers:
        handler = _build_handler(notifier_cfg)
        alerter.add_handler(handler)

    watcher = Watcher(alerter=alerter)

    for job_cfg in config.jobs:
        watcher.register(
            name=job_cfg.name,
            schedule=job_cfg.schedule,
            grace_seconds=job_cfg.grace_seconds,
            max_duration_seconds=job_cfg.max_duration_seconds,
        )

    return watcher
