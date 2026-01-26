#!/bin/sh -e

STORED_DEVICE_ID=$(cat $SNAP_COMMON/configuration/uid)

cp -R $SNAP/etc/configuration/ $SNAP_COMMON/

snapctl set device-uid=$STORED_DEVICE_ID

# Set rob-cos-base-url in confdb if the file exists
if [ -f "$SNAP_COMMON/configuration/rob-cos-base-url" ]; then
    STORED_COS_SERVER_URL=$(cat $SNAP_COMMON/configuration/rob-cos-base-url)
    snapctl set --view :device-cos-settings-control rob-cos-base-url="$STORED_COS_SERVER_URL"
fi

# must be in the SNAP root directory for the find command
cd $SNAP
bash $SNAP/usr/bin/search_and_replace.sh
