#!/bin/sh -e

# Place the ros2-exporter-agent configuration files directly into the
# ros2-exporter-agent snap's writable common configuration directory.
#
# Before overwriting any existing file, a backup is created by appending
# the ".bak" suffix to the destination file.
#
# Requires the system-files interface to be connected:
#   sudo snap connect rob-cos-demo-configuration:ros2-exporter-agent-config

SOURCE="$SNAP/etc/configuration/ros2-exporter-agent"
TARGET="/var/snap/ros2-exporter-agent/common/configuration"

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

    # Back up any pre-existing destination file before overwriting.
    if [ -f "$dest" ]; then
        echo "Backing up $dest -> $dest.bak"
        cp -a "$dest" "$dest.bak"
    fi

    echo "Placing $rel -> $dest"
    cp -a "$SOURCE/$rel" "$dest"
done
