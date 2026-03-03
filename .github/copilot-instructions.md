# rob-cos-demo-configuration: AI Agent Instructions

## Role
**Custodian snap** - Manages the `device-cos-settings` confdb schema and provides configuration to other snaps.

## Key Responsibilities
1. **Confdb Management:** Initialize and validate confdb configuration
2. **Content Sharing:** Expose `$SNAP_COMMON/configuration` via content interface
3. **Placeholder Replacement:** Update live config files from confdb values

## Schema Management

### Editing Schema
```bash
# Edit schema.yaml directly, then sign and acknowledge
../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key schema.yaml

# Verify
snap known confdb-schema account-id=VX84EGFo6txXHSNk4l55reEiaU5n7I7R name=device-cos-settings
```

**Schema Location:** `schema.yaml` (root of repo)
**Current Revision:** 8
**Fields:** device-uid, rob-cos-ip, model-name, registration-server-endpoint

### Schema Structure
```yaml
views:
  control-device-cos-settings:
    rules:
      - request: device-uid
        storage: device.uid
      - request: rob-cos-ip
        storage: cos.rob-cos-ip
```

## Hook Execution Flow

### 1. Install Hook (`snap/hooks/install`)
```bash
# Simple file copy, no configuration logic
cp -r "$SNAP/etc/configuration" "$SNAP_COMMON/"
```

### 2. Connect Hook (`snap/hooks/connect-plug-device-cos-settings-control`)
```python
# Initialize confdb ONLY if empty
- Check existing device-uid
- If empty, read from defaults/device.yaml
- Generate device-uid from /etc/machine-id
- Set all fields with placeholders for IP/model
```

### 3. Change Hook (`snap/hooks/change-view-device-cos-settings-control`)
```python
# Validate + Update
- Validate device-uid length (≥3 chars)
- Validate rob-cos-ip and model-name format
- Trigger search_and_replace.sh
- DO NOT write to uid/rob-cos-base-url files (removed)
```

## Configuration Files Organization

```
snap/local/configuration/
├── defaults/
│   └── device.yaml              # Placeholders ONLY (read once during init)
├── grafana-agent.river          # Live config (updated by search_and_replace.sh)
├── ros2-data-exporter.yaml      # Live config
└── ...

# After install, copied to:
/var/snap/rob-cos-demo-configuration/common/configuration/
```

**Critical:** `defaults/` is for initialization only. Never modify after install.

## search_and_replace.sh Logic

```bash
# 1. Read current values from confdb
CURRENT_DEVICE_ID=$(snapctl get --view :device-cos-settings-observe device-uid)

# 2. Read placeholders from defaults (NO hardcoding, NO fallbacks)
DEFAULTS_FILE="$SNAP/etc/configuration/defaults/device.yaml"
[ ! -f "$DEFAULTS_FILE" ] && echo "ERROR" >&2 && exit 1
STORED_DEVICE_ID=$(grep '^uid:' "$DEFAULTS_FILE" | awk '{print $2}')

# 3. Replace in all files under SNAP_COMMON/configuration
find "$SNAP_COMMON/configuration" -type f -exec sed -i "s#$STORED#$CURRENT#g" {} \;
```

**Must read all placeholders from defaults/device.yaml:**
- `uid: robot-uid-placeholder`
- `rob-cos-ip: rob-cos-ip-placeholder`
- `model-name: model-name-placeholder`

## Snapcraft.yaml Patterns

### Confdb Plugs (Custodian Role)
```yaml
plugs:
  device-cos-settings-control:
    interface: confdb
    account: VX84EGFo6txXHSNk4l55reEiaU5n7I7R
    view: device-cos-settings/control-device-cos-settings
    role: custodian  # Can write

  device-cos-settings-observe:
    interface: confdb
    view: device-cos-settings/observe-device-cos-settings
    role: custodian  # Also has observe view
```

### Content Slot
```yaml
slots:
  configuration-read:
    interface: content
    read: 
      - $SNAP_COMMON/configuration
```

## Building & Testing

### Build
```bash
snapcraft clean && snapcraft
sudo snap install rob-cos-demo-configuration_*.snap --dangerous
```

### Connect & Initialize
```bash
sudo snap connect rob-cos-demo-configuration:device-cos-settings-control
# This triggers connect hook which initializes confdb
```

### Configure Values
```bash
sudo snap run --shell rob-cos-demo-configuration
snapctl set --view :device-cos-settings-control \
    rob-cos-ip="192.168.1.100:8000" \
    model-name="production-fleet"
# This triggers change hook which updates live files
```

### Verify
```bash
# Check confdb
snapctl get --view :device-cos-settings-control -d

# Check live files updated
cat /var/snap/rob-cos-demo-configuration/common/configuration/grafana-agent.river | grep "192.168.1.100"
```

## Common Tasks

### Add New Confdb Field
1. Update `schema.yaml` (add to both views)
2. Add placeholder to `defaults/device.yaml`
3. Update `connect-plug-device-cos-settings-control` hook (initialize field)
4. Update `change-view-device-cos-settings-control` hook (validate field)
5. Update `search_and_replace.sh` (replace placeholder)
6. Sign schema: `../confdb-demo-editing/snapcraft-sign-and-ack -k mirko-test-key schema.yaml`

### Add New Configuration File
1. Add file to `snap/local/configuration/` (use placeholders)
2. Build and install snap (install hook copies it)
3. Configure confdb values (change hook triggers replacement)

### Debug Hook Failures
```bash
sudo journalctl -u snapd -xe | grep "hook"
sudo journalctl -u snapd | grep "snapctl fail"
```

## Anti-Patterns to Avoid
❌ Hardcoding placeholders in scripts  
❌ Writing to uid/rob-cos-base-url files (removed)  
❌ Storing computed values in confdb (compute at runtime)  
❌ Fallback logic in search_and_replace.sh (strict errors only)  
❌ Modifying files in defaults/ after initialization  
