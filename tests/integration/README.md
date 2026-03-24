# Integration testing (alert rules)

This directory holds a **fake Prometheus (and optional Loki) publisher** used to exercise the metric and log lines referenced under `snap/local/configuration/**_alert_rules/`.

It is not a snap test: the snap only ships YAML/JSON templates. The publisher is for **local or CI** checks once you point Prometheus (and optionally Loki) at it, using rendered rules where `%%juju_device_uuid%%` matches `--device-instance`.

## Quick check (CI / smoke)

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tests/integration/requirements.txt
python tests/integration/fake_alert_publisher.py --self-test
```

## Run metrics server

Leave this process running; scrape `http://127.0.0.1:9108/metrics` from Prometheus.

```bash
source .venv/bin/activate
python tests/integration/fake_alert_publisher.py \
  --device-instance integration-test-robot \
  --scenario healthy \
  --host 127.0.0.1 \
  --port 9108
```

Use `--scenario` to pick values aligned with a rule (for example `battery_low`, `motor_overcurrent`). Alert rules with a `for:` duration need that condition to hold for the full window in Prometheus.

## Optional: push one line to Loki

Requires a reachable Loki (`/loki/api/v1/push`).

```bash
source .venv/bin/activate
python tests/integration/fake_alert_publisher.py \
  --device-instance integration-test-robot \
  --scenario healthy \
  --port 9108 \
  --loki-url http://127.0.0.1:3100 \
  --loki-line "E-stop engaged"
```

Use `--loki-job` if your LogQL rule expects a different `job` label than the default `loki.source.journal.read`.

## Automation

GitHub Actions runs `fake_alert_publisher.py --self-test` on pushes and pull requests to `basic` (see `.github/workflows/integration.yaml`).
