"""Command-line entry point for cronwatch."""

import argparse
import logging
import sys
from pathlib import Path

from cronwatch.builder import build_watcher
from cronwatch.config import CronwatchConfig
from cronwatch.daemon import Daemon


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level,
    )


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor cron job execution times and alert on missed or slow runs.",
    )
    parser.add_argument(
        "-c", "--config",
        default="cronwatch.yaml",
        metavar="FILE",
        help="Path to YAML config file (default: cronwatch.yaml)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="How often to check schedules in seconds (default: 60)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)
    logger = logging.getLogger(__name__)

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        return 1

    try:
        config = CronwatchConfig.from_file(config_path)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to load config: %s", exc)
        return 1

    watcher = build_watcher(config)
    daemon = Daemon(watcher, poll_interval=args.poll_interval)
    daemon.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
