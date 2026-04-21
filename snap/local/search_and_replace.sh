#!/bin/sh -e

# function to search and replace keywords in
# SNAP_COMMON's configuration files
search_and_replace() {
    if [ "$#" -ne 2 ]; then
        echo "Usage: search_and_replace <keyword> <replacement>"
        return 1
    fi

    local keyword="$1"
    local replacement="$2"

    local directory="$SNAP_COMMON/configuration"
    local files=$(find "$directory" -type f)

    for file in $files; do
        sed -i "s#$keyword#$replacement#g" "$file"
    done
}

CURRENT_DEVICE_ID=$(snapctl get device-uid)
STORED_DEVICE_ID=$(cat "${SNAP_COMMON}/configuration/uid")

if [ "$CURRENT_DEVICE_ID" != "$STORED_DEVICE_ID" ]; then
    echo "device_id is different updating!"
    search_and_replace "$STORED_DEVICE_ID" "$CURRENT_DEVICE_ID"
fi

CURRENT_S3_ACCESS_KEY_ID=$(snapctl get s3-access-key-id)
STORED_S3_ACCESS_KEY_ID=$(cat $SNAP_COMMON/configuration/s3-access-key-id)

if [ "$CURRENT_S3_ACCESS_KEY_ID" != "$STORED_S3_ACCESS_KEY_ID" ]; then
    echo "s3-access-key-id is different updating!"
    search_and_replace "$STORED_S3_ACCESS_KEY_ID" "$CURRENT_S3_ACCESS_KEY_ID"
fi

CURRENT_S3_SECRET_ACCESS_KEY=$(snapctl get s3-secret-access-key)
STORED_S3_SECRET_ACCESS_KEY=$(cat $SNAP_COMMON/configuration/s3-secret-access-key)

if [ -n "$CURRENT_S3_SECRET_ACCESS_KEY" ] && [ "$CURRENT_S3_SECRET_ACCESS_KEY" != "$STORED_S3_SECRET_ACCESS_KEY" ]; then
    echo "s3-secret-access-key is different updating!"
    search_and_replace "$STORED_S3_SECRET_ACCESS_KEY" "$CURRENT_S3_SECRET_ACCESS_KEY"
fi

CURRENT_COS_SERVER_URL=$(snapctl get rob-cos-base-url)
CURRENT_COS_SERVER_IP=$(echo "$CURRENT_COS_SERVER_URL" | awk -F '//' '{print $2}' | cut -d '/' -f 1)
STORED_COS_SERVER_URL=$(cat "$SNAP_COMMON/configuration/rob-cos-base-url")
STORED_COS_SERVER_IP="$(echo "$STORED_COS_SERVER_URL" | awk -F '//' '{print $2}' | cut -d '/' -f 1)"

if [ "$CURRENT_COS_SERVER_URL" != "$STORED_COS_SERVER_URL" ]; then
    echo "rob-cos-base-url is different updating!"
    search_and_replace "$STORED_COS_SERVER_URL" "$CURRENT_COS_SERVER_URL"
    search_and_replace "$STORED_COS_SERVER_IP" "$CURRENT_COS_SERVER_IP"
fi
