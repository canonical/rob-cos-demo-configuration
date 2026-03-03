#!/bin/sh -e

# Function to search and replace keywords in SNAP_COMMON's configuration files
# This updates live configuration files with values from confdb
search_and_replace() {
    if [ "$#" -ne 2 ]; then
        echo "Usage: search_and_replace <keyword> <replacement>"
        return 0
    fi

    local keyword="$1"
    local replacement="$2"

    local directory="$SNAP_COMMON/configuration"
    local files=$(find "$directory" -type f)

    for file in $files; do
        sed -i "s#$keyword#$replacement#g" "$file"
    done
}

# Get current values from confdb (primary and only source of truth)
CURRENT_DEVICE_ID=$(snapctl get --view :device-cos-settings-observe device-uid 2>/dev/null || echo "")
CURRENT_ROB_COS_IP=$(snapctl get --view :device-cos-settings-observe rob-cos-ip 2>/dev/null || echo "")
CURRENT_MODEL_NAME=$(snapctl get --view :device-cos-settings-observe model-name 2>/dev/null || echo "")

# Get stored placeholders from defaults to know what to replace
DEFAULTS_FILE="$SNAP/etc/configuration/defaults/device.yaml"

# Error if defaults file doesn't exist
if [ ! -f "$DEFAULTS_FILE" ]; then
    echo "ERROR: Defaults file not found at $DEFAULTS_FILE" >&2
    exit 1
fi

# Read all placeholders from defaults file
STORED_DEVICE_ID=$(grep '^uid:' "$DEFAULTS_FILE" | awk '{print $2}')
STORED_ROB_COS_IP=$(grep '^rob-cos-ip:' "$DEFAULTS_FILE" | awk '{print $2}')
STORED_MODEL_NAME=$(grep '^model-name:' "$DEFAULTS_FILE" | awk '{print $2}')

# Verify all placeholders were found
if [ -z "$STORED_DEVICE_ID" ]; then
    echo "ERROR: uid not found in $DEFAULTS_FILE" >&2
    exit 1
fi
if [ -z "$STORED_ROB_COS_IP" ]; then
    echo "ERROR: rob-cos-ip not found in $DEFAULTS_FILE" >&2
    exit 1
fi
if [ -z "$STORED_MODEL_NAME" ]; then
    echo "ERROR: model-name not found in $DEFAULTS_FILE" >&2
    exit 1
fi

# Update device UID in live config files if we have a value from confdb
if [ -n "$CURRENT_DEVICE_ID" ] && [ "$CURRENT_DEVICE_ID" != "$STORED_DEVICE_ID" ]; then
    echo "Updating device_id: $STORED_DEVICE_ID -> $CURRENT_DEVICE_ID"
    search_and_replace "$STORED_DEVICE_ID" "$CURRENT_DEVICE_ID"
fi

# Update rob-cos-ip if configured in confdb and not placeholder
if [ -n "$CURRENT_ROB_COS_IP" ] && [ "$CURRENT_ROB_COS_IP" != "$STORED_ROB_COS_IP" ]; then
    echo "Updating rob-cos-ip: $STORED_ROB_COS_IP -> $CURRENT_ROB_COS_IP"
    search_and_replace "$STORED_ROB_COS_IP" "$CURRENT_ROB_COS_IP"
fi

# Update model-name if configured in confdb and not placeholder
if [ -n "$CURRENT_MODEL_NAME" ] && [ "$CURRENT_MODEL_NAME" != "$STORED_MODEL_NAME" ]; then
    echo "Updating model-name: $STORED_MODEL_NAME -> $CURRENT_MODEL_NAME"
    search_and_replace "$STORED_MODEL_NAME" "$CURRENT_MODEL_NAME"
fi
