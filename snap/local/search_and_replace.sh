#!/bin/sh -e

# Script to update configuration files in $SNAP_COMMON/configuration
# with values from snap configuration (confdb-first architecture)

# Defaults file contains placeholder definitions
DEFAULTS_FILE="$SNAP/etc/configuration/defaults/device.yaml"
CONFIG_DIR="$SNAP_COMMON/configuration"

if [ ! -f "$DEFAULTS_FILE" ]; then
    logger -t rob-cos-demo-configuration "ERROR: Defaults file not found: $DEFAULTS_FILE"
    exit 1
fi

if [ ! -d "$CONFIG_DIR" ]; then
    logger -t rob-cos-demo-configuration "ERROR: Configuration directory not found: $CONFIG_DIR"
    exit 1
fi

# Function to replace placeholder in all config files
search_and_replace() {
    local placeholder="$1"
    local value="$2"
    
    if [ -z "$value" ]; then
        return
    fi
    
    find "$CONFIG_DIR" -type f -exec sed -i "s#${placeholder}#${value}#g" {} \;
}

# Get snap configuration values
ROB_COS_IP=$(snapctl get rob-cos-ip 2>/dev/null || echo "")
MODEL_NAME=$(snapctl get model-name 2>/dev/null || echo "")
ROBOT_UID=$(snapctl get robot-uid 2>/dev/null || echo "")

# Replace placeholders with actual values
if [ -n "$ROB_COS_IP" ]; then
    search_and_replace "rob-cos-ip-placeholder" "$ROB_COS_IP"
    logger -t rob-cos-demo-configuration "Updated rob-cos-ip in configuration files"
fi

if [ -n "$MODEL_NAME" ]; then
    search_and_replace "model-name-placeholder" "$MODEL_NAME"
    logger -t rob-cos-demo-configuration "Updated model-name in configuration files"
fi

if [ -n "$ROBOT_UID" ]; then
    search_and_replace "robot-uid-placeholder" "$ROBOT_UID"
    logger -t rob-cos-demo-configuration "Updated robot-uid in configuration files"
fi

logger -t rob-cos-demo-configuration "Configuration files updated successfully"
