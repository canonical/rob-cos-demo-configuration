#!/usr/bin/env python3
"""
Fake Prometheus (and optional Loki) publisher for integration-testing COS alert rules.

Exposes /metrics with the same series names and labels as
snap/local/configuration/prometheus_alert_rules/*.rules. Point Prometheus at this
process (or use promtool / a scratch Prometheus) with alert rules where
%%juju_device_uuid%% is replaced by the same --device-instance value.

Examples:
  python fake_alert_publisher.py --scenario healthy
  python fake_alert_publisher.py --scenario battery_low
  python fake_alert_publisher.py --loki-url http://127.0.0.1:3100 --loki-line "E-stop engaged"
  python fake_alert_publisher.py --self-test
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from prometheus_client import Counter, Gauge, start_http_server

try:
    import requests
except ImportError:
    requests = None  # type: ignore


def _push_loki_line(
    base_url: str,
    instance: str,
    line: str,
    job: str = "loki.source.journal.read",
) -> None:
    if requests is None:
        raise SystemExit("Install requests (see tests/integration/requirements.txt) for Loki push.")
    ns = str(int(time.time() * 1e9))
    payload = {
        "streams": [
            {
                "stream": {"instance": instance, "job": job},
                "values": [[ns, line]],
            }
        ]
    }
    url = f"{base_url.rstrip('/')}/loki/api/v1/push"
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()


def build_metrics(device_instance: str) -> dict[str, Gauge | Counter]:
    return {
        "ros2_battery_percentage": Gauge(
            "ros2_battery_percentage",
            "Fake battery %",
            labelnames=("device_instance",),
        ),
        "ros2_joint_position_error_radians": Gauge(
            "ros2_joint_position_error_radians",
            "Fake joint tracking error (rad)",
            labelnames=("device_instance",),
        ),
        "ros2_joint_temperature_celsius": Gauge(
            "ros2_joint_temperature_celsius",
            "Fake joint temperature",
            labelnames=("device_instance",),
        ),
        "ros2_payload_mass_kg": Gauge(
            "ros2_payload_mass_kg",
            "Fake payload mass",
            labelnames=("device_instance",),
        ),
        "ros2_payload_rated_mass_kg": Gauge(
            "ros2_payload_rated_mass_kg",
            "Fake rated payload",
            labelnames=("device_instance",),
        ),
        "ros2_cmd_vel_linear_x": Gauge(
            "ros2_cmd_vel_linear_x",
            "Fake cmd_vel linear x",
            labelnames=("device_instance",),
        ),
        "ros2_odometry_linear_velocity": Gauge(
            "ros2_odometry_linear_velocity",
            "Fake odometry linear velocity",
            labelnames=("device_instance",),
        ),
        "ros2_motor_current_amperes": Gauge(
            "ros2_motor_current_amperes",
            "Fake motor current",
            labelnames=("device_instance",),
        ),
        "ros2_lidar_last_message_timestamp_seconds": Gauge(
            "ros2_lidar_last_message_timestamp_seconds",
            "Fake LIDAR last message unix time",
            labelnames=("device_instance",),
        ),
        "node_filesystem_avail_bytes": Gauge(
            "node_filesystem_avail_bytes",
            "Fake filesystem avail",
            labelnames=("device_instance", "mountpoint"),
        ),
        "node_filesystem_size_bytes": Gauge(
            "node_filesystem_size_bytes",
            "Fake filesystem size",
            labelnames=("device_instance", "mountpoint"),
        ),
        "node_cpu_seconds_total": Counter(
            "node_cpu_seconds_total",
            "Fake CPU seconds",
            labelnames=("device_instance", "mode", "cpu"),
        ),
        "node_memory_MemFree_bytes": Gauge(
            "node_memory_MemFree_bytes",
            "Fake MemFree",
            labelnames=("device_instance",),
        ),
        "my_battery__": Gauge(
            "my_battery__",
            "Generic demo battery % (ros2_battery.rules)",
            labelnames=(),
        ),
    }


def apply_scenario(m: dict[str, Gauge | Counter], device_instance: str, scenario: str) -> None:
    di = device_instance

    def set_gauge(name: str, value: float, mountpoint: str | None = None) -> None:
        metric = m[name]
        if mountpoint is not None:
            metric.labels(di, mountpoint).set(value)
        else:
            metric.labels(di).set(value)

    # Defaults (healthy)
    set_gauge("ros2_battery_percentage", 100.0)
    set_gauge("ros2_joint_position_error_radians", 0.0)
    set_gauge("ros2_joint_temperature_celsius", 40.0)
    set_gauge("ros2_payload_mass_kg", 1.0)
    set_gauge("ros2_payload_rated_mass_kg", 50.0)
    set_gauge("ros2_cmd_vel_linear_x", 0.0)
    set_gauge("ros2_odometry_linear_velocity", 0.0)
    set_gauge("ros2_motor_current_amperes", 1.0)
    set_gauge("ros2_lidar_last_message_timestamp_seconds", time.time())
    set_gauge("node_filesystem_avail_bytes", 50e9, mountpoint="/")
    set_gauge("node_filesystem_size_bytes", 100e9, mountpoint="/")
    m["node_memory_MemFree_bytes"].labels(di).set(16e9)
    m["my_battery__"].set(100.0)

    if scenario == "healthy":
        pass
    elif scenario == "battery_low":
        set_gauge("ros2_battery_percentage", 15.0)
    elif scenario == "battery_critical":
        set_gauge("ros2_battery_percentage", 3.0)
    elif scenario == "high_cpu":
        # (1 - avg(rate(idle))) * 100 > 85  → keep idle rate low vs user
        # Background thread continues to increment; see start_cpu_tweaker
        pass
    elif scenario == "low_disk":
        set_gauge("node_filesystem_avail_bytes", 5e9, mountpoint="/")
        set_gauge("node_filesystem_size_bytes", 100e9, mountpoint="/")
    elif scenario == "robot_stuck":
        set_gauge("ros2_cmd_vel_linear_x", 0.5)
        set_gauge("ros2_odometry_linear_velocity", 0.0)
    elif scenario == "motor_overcurrent":
        set_gauge("ros2_motor_current_amperes", 25.0)
    elif scenario == "stale_lidar":
        set_gauge("ros2_lidar_last_message_timestamp_seconds", time.time() - 120.0)
    elif scenario == "joint_tracking_error":
        set_gauge("ros2_joint_position_error_radians", 0.5)
    elif scenario == "joint_overtemperature":
        set_gauge("ros2_joint_temperature_celsius", 85.0)
    elif scenario == "payload_exceeded":
        set_gauge("ros2_payload_mass_kg", 100.0)
        set_gauge("ros2_payload_rated_mass_kg", 10.0)
    elif scenario == "low_memory":
        m["node_memory_MemFree_bytes"].labels(di).set(3e9)
    elif scenario == "generic_low_battery":
        m["my_battery__"].set(5.0)
    else:
        raise SystemExit(f"Unknown scenario: {scenario}")


def start_cpu_tweaker(
    m: dict[str, Gauge | Counter], device_instance: str, scenario: str
) -> threading.Event | None:
    """Drive node_cpu_seconds_total so rate(idle) matches the scenario."""
    if scenario != "high_cpu":
        return None

    stop = threading.Event()

    def run() -> None:
        idle = m["node_cpu_seconds_total"].labels(device_instance, "idle", "0")
        user = m["node_cpu_seconds_total"].labels(device_instance, "user", "0")
        while not stop.wait(0.1):
            idle.inc(0.05)
            user.inc(0.95)

    threading.Thread(target=run, daemon=True).start()
    return stop


def start_lidar_refresh(
    m: dict[str, Gauge | Counter], device_instance: str, scenario: str
) -> threading.Event | None:
    if scenario == "stale_lidar":
        return None
    stop = threading.Event()

    def run() -> None:
        lidar = m["ros2_lidar_last_message_timestamp_seconds"]
        while not stop.wait(1.0):
            lidar.labels(device_instance).set(time.time())

    threading.Thread(target=run, daemon=True).start()
    return stop


def start_default_cpu_idle(
    m: dict[str, Gauge | Counter], device_instance: str, scenario: str
) -> threading.Event | None:
    """Healthy CPU: high idle rate so HighCPUUsage does not fire."""
    if scenario == "high_cpu":
        return None
    stop = threading.Event()

    def run() -> None:
        idle = m["node_cpu_seconds_total"].labels(device_instance, "idle", "0")
        user = m["node_cpu_seconds_total"].labels(device_instance, "user", "0")
        while not stop.wait(0.1):
            idle.inc(0.95)
            user.inc(0.05)

    threading.Thread(target=run, daemon=True).start()
    return stop


def run_self_test() -> None:
    import socket
    import urllib.request

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    m = build_metrics("selftest-uuid")
    apply_scenario(m, "selftest-uuid", "healthy")
    start_http_server(port, addr="127.0.0.1")
    url = f"http://127.0.0.1:{port}/metrics"
    for _ in range(50):
        try:
            with urllib.request.urlopen(url, timeout=0.5) as r:
                body = r.read().decode()
            if "ros2_battery_percentage" in body and "selftest-uuid" in body:
                print("self-test ok:", url)
                return
        except OSError:
            time.sleep(0.05)
    raise SystemExit("self-test failed: /metrics did not become ready or missing expected series")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--device-instance",
        default="integration-test-robot",
        help="Must match device_instance in rendered alert rules (replaces %%juju_device_uuid%%).",
    )
    p.add_argument("--host", default="127.0.0.1", help="Listen address for /metrics.")
    p.add_argument("--port", type=int, default=9108, help="Listen port for /metrics.")
    p.add_argument(
        "--scenario",
        default="healthy",
        choices=[
            "healthy",
            "battery_low",
            "battery_critical",
            "high_cpu",
            "low_disk",
            "low_memory",
            "generic_low_battery",
            "robot_stuck",
            "motor_overcurrent",
            "stale_lidar",
            "joint_tracking_error",
            "joint_overtemperature",
            "payload_exceeded",
        ],
        help="Metric values tuned to eventually satisfy the corresponding Prometheus alerts (subject to for: durations).",
    )
    p.add_argument(
        "--loki-url",
        default="",
        help="If set, push one line to Loki (e.g. http://127.0.0.1:3100) in addition to metrics.",
    )
    p.add_argument(
        "--loki-line",
        default="",
        help="Log line to push (e.g. 'E-stop engaged', 'localization failed', 'Human detected').",
    )
    p.add_argument(
        "--loki-job",
        default="loki.source.journal.read",
        help="Stream job label for Loki (must match LogQL in rules when specified there).",
    )
    p.add_argument(
        "--self-test",
        action="store_true",
        help="Start briefly, fetch /metrics, exit 0 on success (for CI).",
    )
    args = p.parse_args(argv)

    if args.self_test:
        run_self_test()
        return

    m = build_metrics(args.device_instance)
    apply_scenario(m, args.device_instance, args.scenario)

    stops: list[threading.Event] = []
    for starter in (start_default_cpu_idle, start_cpu_tweaker, start_lidar_refresh):
        ev = starter(m, args.device_instance, args.scenario)
        if ev is not None:
            stops.append(ev)

    start_http_server(args.port, addr=args.host)
    print(
        f"Serving Prometheus metrics at http://{args.host}:{args.port}/metrics "
        f"(device_instance={args.device_instance!r}, scenario={args.scenario!r})",
        flush=True,
    )

    if args.loki_url and args.loki_line:
        _push_loki_line(args.loki_url, args.device_instance, args.loki_line, job=args.loki_job)
        print(f"Pushed Loki line to {args.loki_url!r}: {args.loki_line!r}", flush=True)
    elif args.loki_url or args.loki_line:
        print("Both --loki-url and --loki-line are required to push logs.", file=sys.stderr)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        for s in stops:
            s.set()


if __name__ == "__main__":
    main()
