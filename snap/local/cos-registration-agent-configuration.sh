#!/bin/bash -eu

set_confdb_values_from_dir() {
  prefix="$1"
  directory="$2"

  for file in "$directory"/*; do
    if [ -f "$file" ]; then
      name=$(basename "$file")
      name=${name%.*}
      # replace _ with -
      name=${name//_/-}
      # enforce lower_case
      name=${name,,}
      logger -t "${SNAP_NAME}" "Updating confdb key '${prefix}.${name}' from '$file'"
      # add | true so it goes on even if the file is too big
      snapctl set --view -s :cos-registration-agent-configuration "${prefix}.${name}=$(cat "$file")" || true
    fi
  done

}

logger -t "${SNAP_NAME}" "Updating the cos-registration-agent configuration view"

snapctl set --view :cos-registration-agent-configuration "device=$(cat "${SNAP_COMMON}/configuration/device.yaml")"

set_confdb_values_from_dir "foxglove.layouts" "${SNAP_COMMON}/configuration/foxglove_layouts"
set_confdb_values_from_dir "grafana.dashboards" "${SNAP_COMMON}/configuration/grafana_dashboards"
set_confdb_values_from_dir "loki.alerts" "${SNAP_COMMON}/configuration/loki_alert_rules"
set_confdb_values_from_dir "prometheus.alerts" "${SNAP_COMMON}/configuration/prometheus_alert_rules"
