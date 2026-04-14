#!/bin/sh -e

  logger -t "${SNAP_NAME}" "Updating the configuration-file"
  snapctl set --view :otelcol-configuration configuration-file="$(cat $SNAP_COMMON/configuration/otelcol.yaml)"
