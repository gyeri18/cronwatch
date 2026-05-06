"""Tests for the CLI entry point."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli import _parse_args, main


class TestParseArgs:
    def test_defaults(self):
        args = _parse_args([])
        assert args.config == "cronwatch.yaml"
        assert args.poll_interval == 60
        assert not args.verbose

    def test_custom_config(self):
        args = _parse_args(["-c", "my.yaml"])
        assert args.config == "my.yaml"

    def test_verbose_flag(self):
        args = _parse_args(["-v"])
        assert args.verbose

    def test_poll_interval(self):
        args = _parse_args(["--poll-interval", "30"])
        assert args.poll_interval == 30


class TestMain:
    def test_missing_config_returns_1(self, tmp_path):
        result = main(["-c", str(tmp_path / "nonexistent.yaml")])
        assert result == 1

    def test_invalid_config_returns_1(self, tmp_path):
        bad_cfg = tmp_path / "bad.yaml"
        bad_cfg.write_text("not: valid: yaml: [")
        result = main(["-c", str(bad_cfg)])
        assert result == 1

    def test_valid_config_starts_daemon(self, tmp_path):
        cfg = tmp_path / "cronwatch.yaml"
        cfg.write_text(
            "jobs:\n"
            "  - name: test-job\n"
            "    schedule: \"* * * * *\"\n"
            "    timeout: 60\n"
            "notifiers:\n"
            "  - kind: print\n"
        )
        mock_daemon = MagicMock()
        with patch("cronwatch.cli.build_watcher") as mock_build, \
             patch("cronwatch.cli.Daemon", return_value=mock_daemon):
            mock_build.return_value = MagicMock()
            result = main(["-c", str(cfg), "--poll-interval", "10"])
        mock_daemon.start.assert_called_once()
        assert result == 0

    def test_daemon_receives_poll_interval(self, tmp_path):
        cfg = tmp_path / "cronwatch.yaml"
        cfg.write_text(
            "jobs:\n"
            "  - name: j\n"
            "    schedule: \"* * * * *\"\n"
            "    timeout: 30\n"
            "notifiers:\n"
            "  - kind: print\n"
        )
        mock_daemon = MagicMock()
        with patch("cronwatch.cli.build_watcher"), \
             patch("cronwatch.cli.Daemon", return_value=mock_daemon) as MockDaemon:
            main(["-c", str(cfg), "--poll-interval", "120"])
            _, kwargs = MockDaemon.call_args
            assert kwargs.get("poll_interval") == 120 or MockDaemon.call_args[0][1] == 120
