#!/bin/sh -e

# Place the ros2-exporter-agent configuration files directly into the
# ros2-exporter-agent snap's writable common configuration directory.
#
# This script performs placement only; it does NOT create backups. Backups
# are handled exclusively by the connect-plug interface hook.
#
# Requires the system-files interface to be connected:
#   sudo snap connect rob-cos-demo-configuration:ros2-exporter-agent-config

PLUG="ros2-exporter-agent-config"
SOURCE="$SNAP/etc/configuration/ros2-exporter-agent"
TARGET="/var/snap/ros2-exporter-agent/common/configuration"

# Skip quietly if the system-files interface is not connected. This keeps the
# oneshot daemon a no-op until the user connects the interface.
if ! snapctl is-connected "$PLUG"; then
    echo "Interface $PLUG is not connected, skipping configuration placement."
    exit 0
fi

if [ ! -d "$SOURCE" ]; then
    echo "Source directory $SOURCE not found." >&2
    exit 1
fi

if [ ! -d "$TARGET" ]; then
    echo "Target directory $TARGET not found. Is the ros2-exporter-agent snap installed?" >&2
    exit 1
fi

# Iterate over every file in the source tree, preserving relative paths.
cd "$SOURCE"
find . -type f | while read -r file; do
    # Strip the leading "./"
    rel=$(echo "$file" | sed 's#^\./##')
    dest="$TARGET/$rel"
    dest_dir=$(dirname "$dest")

    mkdir -p "$dest_dir"

    echo "Placing $rel -> $dest"
    cp -a "$SOURCE/$rel" "$dest"
done
