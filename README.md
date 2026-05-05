# cronwatch

Lightweight daemon that monitors cron job execution times and alerts on missed or slow runs.

---

## Installation

```bash
pip install cronwatch
```

Or install from source:

```bash
git clone https://github.com/yourname/cronwatch.git && cd cronwatch && pip install .
```

---

## Usage

Define your monitored jobs in `cronwatch.yml`:

```yaml
jobs:
  daily-backup:
    schedule: "0 2 * * *"
    timeout: 300        # alert if runtime exceeds 5 minutes
    grace: 60           # allow 60s late start before alerting
    alert: slack        # notification channel

alerts:
  slack:
    webhook: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

Start the daemon:

```bash
cronwatch start --config cronwatch.yml
```

Wrap your existing cron commands to report execution status:

```bash
# In your crontab
0 2 * * * cronwatch run daily-backup -- /usr/local/bin/backup.sh
```

Check status of monitored jobs:

```bash
cronwatch status
```

---

## Configuration Options

| Key        | Description                              | Default |
|------------|------------------------------------------|---------|
| `schedule` | Cron expression for expected run time    | —       |
| `timeout`  | Max allowed runtime in seconds           | `3600`  |
| `grace`    | Seconds to wait before a missed-run alert| `120`   |
| `alert`    | Alert channel (`slack`, `email`, `pagerduty`) | —  |

---

## License

MIT © 2024 [yourname](https://github.com/yourname)