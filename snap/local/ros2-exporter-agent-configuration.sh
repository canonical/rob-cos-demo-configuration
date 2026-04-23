#!/bin/sh -eu

logger -t "${SNAP_NAME}" "Updating the ros2-exporter-agent configuration-file"
snapctl set --view :ros2-exporter-agent-configuration rclone="$(cat "${SNAP_COMMON}/configuration/ros2-exporter-agent/rclone.conf")"
snapctl set --view :ros2-exporter-agent-configuration rosbag2-recorder="$(cat "${SNAP_COMMON}/configuration/ros2-exporter-agent/rosbag2-recorder.yaml")"
