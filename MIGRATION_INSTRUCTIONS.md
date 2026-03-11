# Confdb Migration Instructions

## Overview

This document provides comprehensive instructions for migrating `rob-cos-demo-configuration` from a file-based configuration management approach to a confdb-based approach. The confdb will serve as the single source of truth for configuration data, with files only used for initial default values during installation.

### Current State

- **Custodian Snap**: `rob-cos-demo-configuration` - manages configuration for COS (Cloud Observability Stack) on devices
- **Observer Snap**: `cos-registration-agent` - reads configuration to register devices
- **Current Approach**: File-based configuration with placeholder values that are replaced via `search_and_replace.sh`
- **Target Approach**: Confdb-based configuration with files only for initial defaults

### Placeholders to Migrate

The following placeholders are currently used throughout configuration files and need to be migrated to confdb:

1. **`robot-uid-placeholder`** - The unique device/robot identifier
2. **`rob-cos-ip-placeholder`** - The IP address or hostname of the COS server
3. **`model-name-placeholder`** - The model/deployment name

These placeholders appear in:
- `snap/local/configuration/uid`
- `snap/local/configuration/rob-cos-base-url`
- `snap/local/configuration/device.yaml`
- `snap/local/configuration/grafana-agent.river`
- `snap/local/configuration/ros2-data-exporter.yaml`

### Confdb Schema Location

- **Schema File**: `schema.yaml` (in this repository)
- **Signing Script**: `../confdb-demo-editing/snapcraft-sign-and-ack`
- **Key Name**: `mirko-test-key`

---

## Part 1: Understanding Confdb Operations

### Reading from Confdb

Confdb values are read using `snapctl get --view <view-name> <key>`. The view name is prefixed with `:` to indicate it's a confdb view (not snap config).

#### Example: Using Python (from cos-registration-agent)

```python
import json
import subprocess
from typing import Optional

def get_confdb_value(view: str, key: Optional[str] = None) -> Optional[dict]:
    """Get configuration value from confdb view.

    Args:
        view (str): The confdb view name (e.g., ':device-cos-settings-observe')
        key (str, optional): Specific key to retrieve. If None, returns all data.

    Returns:
        dict or str: The configuration data, or None if not available.
    """
    try:
        cmd = ["snapctl", "get", "--view", view, "-d"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if proc.returncode != 0:
            return None
        
        data = json.loads(proc.stdout)
        
        if key:
            return data.get(key)
        
        return data
    
    except json.JSONDecodeError as e:
        return None
    except Exception as e:
        return None

# Usage example
data = get_confdb_value(":device-cos-settings-observe")
base_url = data.get("rob-cos-base-url") if data else None
```

#### Example: Using Shell

```bash
#!/bin/sh

# Get entire view as JSON
snapctl get --view :device-cos-settings-observe -d

# Get specific value
BASE_URL=$(snapctl get --view :device-cos-settings-observe rob-cos-base-url 2>/dev/null || echo "")

# Check if value exists
if [ -n "$BASE_URL" ]; then
    echo "Base URL: $BASE_URL"
else
    echo "No base URL configured"
fi
```

### Writing to Confdb

Only the custodian snap can write to confdb using `snapctl set --view <view-name> <key>=<value>`.

#### Example: Using Python (from proxy-confdb-demo change-view hook)

```python
#!/usr/bin/env python3
import json
import subprocess

# Get current configuration
cmd = "snapctl get --view :device-cos-settings-control -d"
proc = subprocess.run(cmd.split(), capture_output=True, text=True)

if proc.returncode != 0:
    cmd = f"snapctl fail {proc.stderr}"
    subprocess.run(cmd.split())
    exit(1)

config = json.loads(proc.stdout)

# Validate and modify configuration
device_uid = config.get("device-uid")
if device_uid and len(device_uid) < 5:
    cmd = f"snapctl fail Device UID must be at least 5 characters"
    subprocess.run(cmd.split())
    exit(1)

# Set a value back (if needed)
# snapctl set --view :device-cos-settings-control device-uid="new-value"
```

#### Example: Using Shell

```bash
#!/bin/sh

# Set a single value
snapctl set --view :device-cos-settings-control rob-cos-base-url="http://192.168.1.100:8000"

# Set multiple values
snapctl set --view :device-cos-settings-control \
    device-uid="robot-12345" \
    rob-cos-base-url="http://192.168.1.100:8000"

# Set JSON array or complex value
snapctl set --view :device-cos-settings-control -t \
    model-name="prod-deployment"
```

---

## Part 2: Updating the Confdb Schema

### Current Schema

The current `schema.yaml` defines:

```yaml
account-id: VX84EGFo6txXHSNk4l55reEiaU5n7I7R
name: device-cos-settings
summary: Summary of the confdb-schema
# revision: 1
views:
  wifi-setup:
    summary: Summary of the view.
    rules:
      - request: ssids
        storage: wifi.ssids
        access: read

body: |-
  {
    "storage": {
      "schema": {
        "wifi": {
          "values": "any"
        }
      }
    }
  }
```

### Required Changes

The schema needs to be updated to include all configuration fields. Here's the complete updated schema:

```yaml
account-id: VX84EGFo6txXHSNk4l55reEiaU5n7I7R
name: device-cos-settings
summary: Configuration schema for device COS settings including device identity and server endpoints
# The revision for this confdb-schema
# revision: 5
views:
  control-device-cos-settings:
    summary: Complete read-write access to device COS settings (custodian only)
    rules:
      - request: device-uid
        storage: device.uid
        access: read-write
      - request: rob-cos-base-url
        storage: cos.base-url
        access: read-write
      - request: model-name
        storage: cos.model-name
        access: read-write
      - request: registration-server-endpoint
        storage: cos.registration-server-endpoint
        access: read-write
  
  observe-device-cos-settings:
    summary: Read-only access to device COS settings
    rules:
      - request: device-uid
        storage: device.uid
        access: read
      - request: rob-cos-base-url
        storage: cos.base-url
        access: read
      - request: model-name
        storage: cos.model-name
        access: read
      - request: registration-server-endpoint
        storage: cos.registration-server-endpoint
        access: read

body: |-
  {
    "storage": {
      "schema": {
        "device": {
          "schema": {
            "uid": "string"
          }
        },
        "cos": {
          "schema": {
            "base-url": "string",
            "model-name": "string",
            "registration-server-endpoint": "string"
          }
        }
      }
    }
  }
```

### Signing and Acknowledging the Schema

Use the `snapcraft-sign-and-ack` script from `confdb-demo-editing`:

```bash
# From the rob-cos-demo-configuration directory
cd /home/mirko/canonical/confdb-work/rob-cos-demo-configuration

# Sign and acknowledge the schema with auto-bump
../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key schema.yaml

# This will:
# 1. Auto-bump the revision (1 -> 2, 2 -> 3, etc.)
# 2. Convert YAML to JSON using yaml-to-sign-json.py
# 3. Sign with mirko-test-key using 'snap sign'
# 4. Acknowledge with 'snap ack'

# To sign without auto-bump (manual revision control):
../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key --no-bump schema.yaml

# To dry-run (see what would happen):
../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key --dry-run schema.yaml
```

**Important**: Ensure the account-id in `schema.yaml` matches your signing key's account ID. The key must already exist in snapd (`snap keys` to verify).

---

## Part 3: Migration Plan

### Step 1: Update Schema and Snapcraft.yaml

**Files to modify**:
- `schema.yaml` - Add new fields (see Part 2)
- `snap/snapcraft.yaml` - Ensure confdb plugs are present

The `snapcraft.yaml` already has the confdb plugs defined:

```yaml
plugs:
  device-cos-settings-control:
    interface: confdb
    account: VX84EGFo6txXHSNk4l55reEiaU5n7I7R
    view: device-cos-settings/control-device-cos-settings
    role: custodian

  device-cos-settings-observe:
    interface: confdb
    account: VX84EGFo6txXHSNk4l55reEiaU5n7I7R
    view: device-cos-settings/observe-device-cos-settings
    role: custodian
```

### Step 2: Update Hooks

#### 2a. Update `snap/hooks/connect-plug-device-cos-settings-control`

This hook runs when the confdb plug is connected. It should initialize confdb with default values from files if confdb is empty:

```bash
#!/bin/sh -e

# Check if confdb already has data
EXISTING_UID=$(snapctl get --view :device-cos-settings-control device-uid 2>/dev/null || echo "")

if [ -z "$EXISTING_UID" ]; then
    # First-time setup: Initialize confdb from default files
    logger -t ${SNAP_NAME} "Initializing confdb from default configuration files"
    
    # Initialize device UID
    if [ -f "$SNAP_COMMON/configuration/uid" ]; then
        DEVICE_UID=$(cat "$SNAP_COMMON/configuration/uid")
    else
        # Generate if file doesn't exist
        DEVICE_UID=$(bash "$SNAP/usr/bin/generate_device_uid.sh")
    fi
    
    # Extract values from rob-cos-base-url file
    if [ -f "$SNAP_COMMON/configuration/rob-cos-base-url" ]; then
        BASE_URL_FULL=$(cat "$SNAP_COMMON/configuration/rob-cos-base-url")
        # Extract IP/hostname: http://rob-cos-ip-placeholder/model-name-placeholder
        ROB_COS_IP=$(echo "$BASE_URL_FULL" | sed -E 's|http://([^/]+)/.*|\1|')
        MODEL_NAME=$(echo "$BASE_URL_FULL" | sed -E 's|http://[^/]+/(.*)|\1|')
        BASE_URL="http://${ROB_COS_IP}"
    else
        BASE_URL="http://localhost:8000"
        MODEL_NAME="default-model"
    fi
    
    # Set all values in confdb
    snapctl set --view :device-cos-settings-control \
        device-uid="$DEVICE_UID" \
        rob-cos-base-url="$BASE_URL" \
        model-name="$MODEL_NAME" \
        registration-server-endpoint="-cos-registration-server"
    
    logger -t ${SNAP_NAME} "Initialized confdb: device-uid=$DEVICE_UID, base-url=$BASE_URL, model=$MODEL_NAME"
else
    logger -t ${SNAP_NAME} "Confdb already initialized, skipping default setup"
fi
```

#### 2b. Update `snap/hooks/change-view-device-cos-settings-control`

This hook runs whenever confdb values are modified. Add validation and auto-update file-based configuration for backward compatibility:

```python
#!/usr/bin/env python3

import json
import subprocess
import os
import sys

# Get the current confdb configuration
cmd = "snapctl get --view :device-cos-settings-control -d"
proc = subprocess.run(cmd.split(), capture_output=True, text=True)

if proc.returncode != 0:
    # First time setup - no data yet, this is OK
    sys.exit(0)

try:
    config = json.loads(proc.stdout)
except json.JSONDecodeError:
    sys.exit(0)

# Validation
device_uid = config.get("device-uid", "")
rob_cos_base_url = config.get("rob-cos-base-url", "")
model_name = config.get("model-name", "")

# Validate device UID
if device_uid and len(device_uid) < 3:
    cmd = "snapctl fail Device UID must be at least 3 characters"
    subprocess.run(cmd.split())
    sys.exit(1)

# Validate base URL format
if rob_cos_base_url:
    if not (rob_cos_base_url.startswith("http://") or rob_cos_base_url.startswith("https://")):
        cmd = "snapctl fail Base URL must start with http:// or https://"
        subprocess.run(cmd.split())
        sys.exit(1)

# Validate model name
if model_name and len(model_name) < 1:
    cmd = "snapctl fail Model name cannot be empty"
    subprocess.run(cmd.split())
    sys.exit(1)

# Update configuration files for backward compatibility
# This allows snaps that still read files to get updated values
try:
    snap_common = os.environ.get("SNAP_COMMON", "/var/snap/rob-cos-demo-configuration/common")
    
    # Update uid file
    if device_uid:
        uid_file = os.path.join(snap_common, "configuration", "uid")
        with open(uid_file, 'w') as f:
            f.write(device_uid + '\n')
    
    # Update rob-cos-base-url file
    if rob_cos_base_url and model_name:
        url_file = os.path.join(snap_common, "configuration", "rob-cos-base-url")
        full_url = f"{rob_cos_base_url.rstrip('/')}/{model_name}"
        with open(url_file, 'w') as f:
            f.write(full_url + '\n')
    
    # Trigger search and replace to update all config files
    search_replace = os.path.join(os.environ.get("SNAP", ""), "usr/bin/search_and_replace.sh")
    if os.path.exists(search_replace):
        subprocess.run(["/bin/bash", search_replace], check=False)
    
except Exception as e:
    # Don't fail the hook if file updates fail - confdb is the source of truth
    print(f"Warning: Could not update configuration files: {e}", file=sys.stderr)

sys.exit(0)
```

#### 2c. Update `snap/hooks/install`

Simplify the install hook - just copy files, don't set snap config:

```bash
#!/bin/sh -e

# Copy default configuration files to SNAP_COMMON
cp -R $SNAP/etc/configuration/ $SNAP_COMMON/

# Note: Device UID generation and confdb initialization now happens in
# connect-plug-device-cos-settings-control hook
```

#### 2d. Update `snap/hooks/configure`

The configure hook can be simplified or removed since confdb is now the primary configuration method:

```bash
#!/bin/sh -e

# Legacy configure hook - kept for backward compatibility
# Configuration now primarily managed via confdb

# If needed, you can still support snap config as a way to update confdb:
# DEVICE_UID=$(snapctl get device-uid 2>/dev/null || echo "")
# if [ -n "$DEVICE_UID" ]; then
#     snapctl set --view :device-cos-settings-control device-uid="$DEVICE_UID"
# fi
```

### Step 3: Update Helper Scripts

#### 3a. Modify `snap/local/search_and_replace.sh`

Update to read from confdb instead of snap config:

```bash
#!/bin/sh -e

# Function to search and replace keywords in SNAP_COMMON's configuration files
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

# Get current values from confdb (primary source)
DEVICE_UID=$(snapctl get --view :device-cos-settings-observe device-uid 2>/dev/null || echo "")
ROB_COS_BASE_URL=$(snapctl get --view :device-cos-settings-observe rob-cos-base-url 2>/dev/null || echo "")
MODEL_NAME=$(snapctl get --view :device-cos-settings-observe model-name 2>/dev/null || echo "")

# Get stored placeholder values from files
STORED_DEVICE_UID=$(cat $SNAP_COMMON/configuration/uid 2>/dev/null || echo "robot-uid-placeholder")
STORED_COS_SERVER_URL=$(cat $SNAP_COMMON/configuration/rob-cos-base-url 2>/dev/null || echo "http://rob-cos-ip-placeholder/model-name-placeholder")

# Extract IP and model from stored URL
STORED_COS_SERVER_IP=$(echo "$STORED_COS_SERVER_URL" | awk -F '//' '{print $2}' | cut -d '/' -f 1)
STORED_MODEL_NAME=$(echo "$STORED_COS_SERVER_URL" | awk -F '/' '{print $NF}')

# Update device UID if changed
if [ -n "$DEVICE_UID" ] && [ "$DEVICE_UID" != "$STORED_DEVICE_UID" ]; then
    echo "Device UID changed: $STORED_DEVICE_UID -> $DEVICE_UID"
    search_and_replace "$STORED_DEVICE_UID" "$DEVICE_UID"
    echo "$DEVICE_UID" > "$SNAP_COMMON/configuration/uid"
fi

# Update base URL if changed
if [ -n "$ROB_COS_BASE_URL" ]; then
    CURRENT_COS_SERVER_IP=$(echo "$ROB_COS_BASE_URL" | awk -F '//' '{print $2}' | cut -d '/' -f 1)
    
    if [ "$CURRENT_COS_SERVER_IP" != "$STORED_COS_SERVER_IP" ]; then
        echo "COS Server IP changed: $STORED_COS_SERVER_IP -> $CURRENT_COS_SERVER_IP"
        search_and_replace "$STORED_COS_SERVER_IP" "$CURRENT_COS_SERVER_IP"
    fi
fi

# Update model name if changed
if [ -n "$MODEL_NAME" ] && [ "$MODEL_NAME" != "$STORED_MODEL_NAME" ]; then
    echo "Model name changed: $STORED_MODEL_NAME -> $MODEL_NAME"
    search_and_replace "$STORED_MODEL_NAME" "$MODEL_NAME"
fi

# Update the stored URL file with new values
if [ -n "$ROB_COS_BASE_URL" ] && [ -n "$MODEL_NAME" ]; then
    NEW_URL="${ROB_COS_BASE_URL}/${MODEL_NAME}"
    echo "$NEW_URL" > "$SNAP_COMMON/configuration/rob-cos-base-url"
fi
```

### Step 4: Update Observer Snap (cos-registration-agent)

The `cos-registration-agent` already has confdb reading capability through `confdb_utils.py`. Update it to read the new fields:

#### 4a. Update `cos_registration_agent/confdb_utils.py`

Add functions for new fields:

```python
def get_device_uid() -> Optional[str]:
    """Get device UID from confdb.

    Returns:
        str: The device UID, or None if not available.
    """
    data = get_confdb_value(":device-cos-settings-observe")
    if data:
        return data.get("device-uid")
    return None


def get_model_name() -> Optional[str]:
    """Get model name from confdb.

    Returns:
        str: The model name, or None if not available.
    """
    data = get_confdb_value(":device-cos-settings-observe")
    if data:
        return data.get("model-name")
    return None


def get_full_base_url() -> Optional[str]:
    """Get complete base URL including model name.
    
    Combines rob-cos-base-url and model-name.

    Returns:
        str: The complete base URL, or None if not available.
    """
    data = get_confdb_value(":device-cos-settings-observe")
    if not data:
        return None
    
    base_url = data.get("rob-cos-base-url")
    model_name = data.get("model-name")
    
    if not base_url:
        return None
    
    base_url = base_url.rstrip("/")
    
    if model_name:
        return f"{base_url}/{model_name}"
    else:
        return base_url
```

---

## Part 4: Testing the Migration

### Prerequisites

```bash
# Enable confdb feature in snapd
sudo snap set system experimental.confdb=true
snap restart snapd

# Verify mirko-test-key exists
snap keys | grep mirko-test-key
```

### Testing Steps

#### 1. Update and Sign Schema

```bash
cd /home/mirko/canonical/confdb-work/rob-cos-demo-configuration

# Edit schema.yaml with the new fields (see Part 2)
# Then sign and acknowledge
../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key schema.yaml

# Verify schema is acknowledged
snap known confdb-schema account-id=VX84EGFo6txXHSNk4l55reEiaU5n7I7R name=device-cos-settings
```

#### 2. Build and Install Updated Snap

```bash
# Make sure hooks are executable
chmod +x snap/hooks/*

# Build
snapcraft clean
snapcraft

# Install
sudo snap install rob-cos-demo-configuration_*.snap --dangerous
```

#### 3. Connect Confdb Interface

```bash
# Connect the confdb plug (triggers connect hook)
sudo snap connect rob-cos-demo-configuration:device-cos-settings-control

# This should initialize confdb with default values from files
```

#### 4. Verify Initialization

```bash
# Check confdb values
sudo snap run --shell rob-cos-demo-configuration
# Inside shell:
snapctl get --view :device-cos-settings-control -d | jq

# Should show all fields: device-uid, rob-cos-base-url, model-name, registration-server-endpoint
```

#### 5. Test Updates

```bash
# Update a value
sudo snap run --shell rob-cos-demo-configuration
snapctl set --view :device-cos-settings-control \
    rob-cos-base-url="http://192.168.1.100:8000" \
    model-name="production-fleet"

# Verify change hook ran successfully
journalctl -u snapd | grep rob-cos-demo-configuration

# Check that files were updated for backward compatibility
cat /var/snap/rob-cos-demo-configuration/common/configuration/rob-cos-base-url
# Should show: http://192.168.1.100:8000/production-fleet
```

#### 6. Test Observer Access (cos-registration-agent)

```bash
# Build and install cos-registration-agent
cd /home/mirko/canonical/confdb-work/cos-registration-agent
snapcraft
sudo snap install cos-registration-agent_*.snap --dangerous

# Connect confdb
sudo snap connect cos-registration-agent:device-cos-settings-observe

# Test reading from confdb
sudo snap run --shell cos-registration-agent
python3 << 'EOF'
from cos_registration_agent.confdb_utils import get_confdb_value
data = get_confdb_value(":device-cos-settings-observe")
print(data)
EOF
```

---

## Part 5: File Reference Guide

### Key Files and Their Purposes

#### rob-cos-demo-configuration Repository

| File | Purpose |
|------|---------|
| `schema.yaml` | Confdb schema definition (YAML format for editing) |
| `schema.json` | Auto-generated JSON for signing |
| `schema-signed.assert` | Signed confdb schema assertion |
| `snap/snapcraft.yaml` | Snap package definition with confdb plugs |
| `snap/hooks/connect-plug-device-cos-settings-control` | Initialize confdb on plug connection |
| `snap/hooks/change-view-device-cos-settings-control` | Validate and sync confdb changes |
| `snap/hooks/install` | Install hook - copy default files |
| `snap/hooks/configure` | Legacy configure hook |
| `snap/local/search_and_replace.sh` | Update config files based on confdb values |
| `snap/local/generate_device_uid.sh` | Generate unique device ID |
| `snap/local/configuration/*` | Default configuration files with placeholders |

#### confdb-demo-editing Repository

| File | Purpose |
|------|---------|
| `snapcraft-sign-and-ack` | Bash script to sign and acknowledge schemas |
| `yaml-to-sign-json.py` | Convert YAML schema to JSON for signing |

#### cos-registration-agent Repository

| File | Purpose |
|------|---------|
| `cos_registration_agent/confdb_utils.py` | Helper functions to read from confdb |
| `snap/snapcraft.yaml` | Includes device-cos-settings-observe plug |

#### proxy-confdb-demo Repository (Reference)

| File | Purpose |
|------|---------|
| `docs/ephemeral-data.md` | Documentation on ephemeral data pattern |
| `net-ctrl/snap/hooks/change-view-proxy-control` | Example change-view hook |
| `net-ctrl/snap/snapcraft.yaml` | Example custodian snap with confdb plugs |

---

## Part 6: Command Reference

### Confdb Operations

```bash
# Read entire view
snapctl get --view :device-cos-settings-observe -d

# Read specific key
snapctl get --view :device-cos-settings-observe device-uid

# Write single value (custodian only)
snapctl set --view :device-cos-settings-control device-uid="robot-12345"

# Write multiple values
snapctl set --view :device-cos-settings-control \
    device-uid="robot-12345" \
    rob-cos-base-url="http://192.168.1.100:8000"

# Write with type flag (for JSON values)
snapctl set --view :device-cos-settings-control -t model-name="prod"
```

### Schema Management

```bash
# Sign and acknowledge schema
../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key schema.yaml

# Sign without auto-bump
../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key --no-bump schema.yaml

# Dry run
../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key --dry-run schema.yaml

# Query known schemas
snap known confdb-schema account-id=VX84EGFo6txXHSNk4l55reEiaU5n7I7R

# Query specific schema
snap known confdb-schema account-id=VX84EGFo6txXHSNk4l55reEiaU5n7I7R name=device-cos-settings
```

### Interface Management

```bash
# Connect confdb plugs
sudo snap connect rob-cos-demo-configuration:device-cos-settings-control
sudo snap connect rob-cos-demo-configuration:device-cos-settings-observe
sudo snap connect cos-registration-agent:device-cos-settings-observe

# List connections
snap connections rob-cos-demo-configuration
snap connections cos-registration-agent

# Disconnect
sudo snap disconnect rob-cos-demo-configuration:device-cos-settings-control
```

### Debugging

```bash
# View hook execution logs
journalctl -u snapd -f | grep rob-cos-demo-configuration

# Run snap in shell for manual testing
sudo snap run --shell rob-cos-demo-configuration

# Check snap config vs confdb
snapctl get -d  # snap config
snapctl get --view :device-cos-settings-control -d  # confdb

# View change hook triggered events
journalctl -u snapd | grep change-view-device-cos-settings-control
```

---

## Part 7: Migration Checklist

Use this checklist to track migration progress:

- [ ] **Schema Update**
  - [ ] Update `schema.yaml` with new fields (device-uid, model-name)
  - [ ] Uncomment revision line and set to next number
  - [ ] Update summary to describe all fields
  - [ ] Update both views (control and observe)
  - [ ] Update body schema to include device.uid and cos.model-name

- [ ] **Sign and Acknowledge Schema**
  - [ ] Run `snapcraft-sign-and-ack` with mirko-test-key
  - [ ] Verify schema acknowledged: `snap known confdb-schema`
  - [ ] Save `schema-signed.assert` to repository

- [ ] **Update Hooks**
  - [ ] Update `connect-plug-device-cos-settings-control` for initialization
  - [ ] Update `change-view-device-cos-settings-control` for validation
  - [ ] Simplify `install` hook
  - [ ] Update or remove `configure` hook
  - [ ] Make all hooks executable: `chmod +x snap/hooks/*`

- [ ] **Update Scripts**
  - [ ] Update `search_and_replace.sh` to read from confdb
  - [ ] Test placeholder replacement with new confdb values

- [ ] **Build and Test rob-cos-demo-configuration**
  - [ ] Build snap: `snapcraft`
  - [ ] Install: `sudo snap install *.snap --dangerous`
  - [ ] Connect plug: `sudo snap connect :device-cos-settings-control`
  - [ ] Verify confdb initialized: `snapctl get --view :device-cos-settings-control -d`
  - [ ] Test updates: `snapctl set --view :device-cos-settings-control ...`
  - [ ] Verify files updated for backward compatibility

- [ ] **Update cos-registration-agent**
  - [ ] Add helper functions in `confdb_utils.py`
  - [ ] Update CLI to use confdb functions
  - [ ] Test reading configuration from confdb

- [ ] **Integration Testing**
  - [ ] Both snaps installed and connected
  - [ ] Observer can read configuration
  - [ ] Updates in custodian visible to observer
  - [ ] Fallback to files works if confdb unavailable

- [ ] **Documentation**
  - [ ] Update main README.md with confdb instructions
  - [ ] Document configuration management workflow
  - [ ] Add troubleshooting section

---

## Part 8: Troubleshooting

### Common Issues

#### Schema Not Acknowledged

**Symptom**: `snap known confdb-schema` doesn't show your schema

**Solutions**:
1. Check if confdb feature is enabled: `snap get system experimental.confdb`
2. Verify account-id matches your key: `snap keys`
3. Check for signing errors in `snapcraft-sign-and-ack` output
4. Try manually: `cat schema.json | snap sign -k mirko-test-key | snap ack`

#### Confdb Plug Not Connecting

**Symptom**: `snap connect` fails with permission error

**Solutions**:
1. Ensure schema is acknowledged first
2. Verify account-id in `snapcraft.yaml` matches schema
3. Check view name matches: `device-cos-settings/control-device-cos-settings`
4. Look at snapd logs: `journalctl -u snapd | tail -50`

#### Hook Failures

**Symptom**: Hook fails, preventing snap operations

**Solutions**:
1. Check hook logs: `journalctl -u snapd | grep hook`
2. Add debug output to hooks: `echo "Debug: variable=$var" >&2`
3. Test hook manually: `sudo snap run --shell <snap>` then run hook script
4. Fix and rebuild, then refresh snap

#### Confdb Read Returns Empty

**Symptom**: `snapctl get --view` returns empty or error

**Solutions**:
1. Confirm plug is connected: `snap connections`
2. Check if confdb was initialized in connect hook
3. Verify view name is correct (`:device-cos-settings-observe` with colon)
4. Try control view if you're in custodian snap

#### Values Not Updating in Files

**Symptom**: Confdb values update but files stay old

**Solutions**:
1. Check if `change-view` hook is executing: `journalctl -u snapd`
2. Verify `search_and_replace.sh` is being called from hook
3. Check file permissions in `$SNAP_COMMON/configuration/`
4. Add logging to `change-view` hook to debug

---

## Summary

This migration moves `rob-cos-demo-configuration` from file-based configuration to confdb-based configuration:

1. **Files → Confdb**: All configuration stored in confdb (device-uid, rob-cos-base-url, model-name)
2. **Initialization**: Files only used for initial defaults during first connection
3. **Updates**: All updates done via confdb (custodian writes, observers read)
4. **Backward Compatibility**: Optional file sync in change-view hook for legacy components

**Key Benefits**:
- Centralized configuration management
- Real-time updates to all connected snaps
- Validation through change-view hooks
- Better integration with snapd ecosystem

**Next Steps**:
1. Update schema.yaml with all fields
2. Sign and acknowledge the schema
3. Update hooks for initialization and validation
4. Build, install, and test
5. Update observer snaps to read from confdb
