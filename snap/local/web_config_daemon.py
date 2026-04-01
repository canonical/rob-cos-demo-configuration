#!/usr/bin/env python3
"""
Web configuration daemon - self-contained.
Provides web UI for configuration and handles sync while running.
User-controlled daemon (optional).
"""

import os
import subprocess
import sys
import time
import logging.handlers
import threading
import socket
from flask import Flask, render_template, request, jsonify

# Add snap lib to Python path
snap_dir = os.environ.get("SNAP", "")
if snap_dir:
    sys.path.insert(0, os.path.join(snap_dir, "usr/lib"))

from configure_logic import CONFIG_MAPPINGS, set_confdb_data, get_snap_config_values, setup_logger

# Setup logging
logger = setup_logger("web-config-daemon")

# State file to track last known config values (separate from background daemon)
STATE_FILE = os.path.join(
    os.environ.get("SNAP_DATA", "/tmp"),
    "web-config-state.txt"
)

# Flask app for web UI
app = Flask(__name__, 
            template_folder=os.path.join(snap_dir, "usr/share/web_config/templates") if snap_dir else "templates",
            static_folder=os.path.join(snap_dir, "usr/share/web_config/static") if snap_dir else "static")

# Configuration fields for web UI
CONFIG_FIELDS = {
    "rob-cos-ip": {
        "label": "COS Server IP Address",
        "placeholder": "e.g., 192.168.1.100",
        "type": "text",
        "required": True
    },
    "model-name": {
        "label": "Model Name",
        "placeholder": "e.g., cos-robotics-model",
        "type": "text",
        "required": True
    },
    "robot-uid": {
        "label": "Robot UID",
        "placeholder": "e.g., robot-12345",
        "type": "text",
        "required": True
    }
}


def get_snap_config(key):
    """Get snap configuration value."""
    try:
        result = subprocess.run(
            ["snapctl", "get", key],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def set_snap_config(key, value):
    """Set snap configuration value using snapctl."""
    try:
        result = subprocess.run(
            ["snapctl", "set", f"{key}={value}"],
            capture_output=True,
            text=True,
            check=True
        )
        return True, "Success"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to set {key}: {e.stderr}"
    except Exception as e:
        return False, str(e)


@app.route('/')
def index():
    """Render the configuration page."""
    return render_template('index.html', fields=CONFIG_FIELDS)


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration values."""
    config = {}
    for key in CONFIG_FIELDS.keys():
        config[key] = get_snap_config(key)
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
def set_config():
    """Set configuration values via snap config."""
    data = request.json
    errors = []
    
    # Validate all required fields are present
    for key, field_info in CONFIG_FIELDS.items():
        if field_info.get('required') and not data.get(key):
            errors.append(f"{field_info['label']} is required")
    
    if errors:
        return jsonify({"success": False, "errors": errors}), 400
    
    # Set each snap configuration value
    for key in CONFIG_FIELDS.keys():
        if key in data:
            success, message = set_snap_config(key, data[key])
            if not success:
                errors.append(message)
    
    if errors:
        return jsonify({"success": False, "errors": errors}), 500
    
    return jsonify({
        "success": True, 
        "message": "Configuration values set. Sync will update confdb shortly."
    })


def get_local_ip():
    """Get the local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def load_last_state():
    """Load the last known configuration state."""
    if not os.path.exists(STATE_FILE):
        return {}
    
    try:
        state = {}
        with open(STATE_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    state[key] = value
        return state
    except Exception as e:
        logger.warning(f"Failed to load state file: {e}")
        return {}


def save_state(config_values):
    """Save current configuration state."""
    try:
        with open(STATE_FILE, 'w') as f:
            for key, value in config_values.items():
                if value:
                    f.write(f"{key}={value}\n")
    except Exception as e:
        logger.warning(f"Failed to save state file: {e}")


def config_changed(current_config, last_config):
    """Check if configuration has changed."""
    for key in CONFIG_MAPPINGS.keys():
        if current_config.get(key) != last_config.get(key):
            return True
    return False


def sync_loop():
    """Configuration sync loop - runs while web UI is active."""
    logger.info("Web config sync loop started")
    
    # Check interval in seconds
    check_interval = 5
    
    last_config = load_last_state()
    
    while True:
        try:
            # Get current snap configuration values
            current_config = get_snap_config_values()
            
            # Check if configuration has changed
            if config_changed(current_config, last_config):
                logger.info("Configuration change detected")
                
                # Check if all required values are present
                all_set = all(current_config.get(key) for key in CONFIG_MAPPINGS.keys())
                
                if all_set:
                    logger.info("All configuration values present, syncing to confdb")
                    
                    # Sync to confdb
                    success, message = set_confdb_data(current_config, logger)
                    
                    if success:
                        logger.info("Successfully synced configuration to confdb")
                        # Update state only on success
                        save_state(current_config)
                        last_config = current_config
                    else:
                        logger.warning(f"Failed to sync to confdb: {message}")
                else:
                    # Some values are missing - clear the state
                    logger.info("Configuration incomplete, clearing state")
                    save_state({})
                    last_config = {}
            
            # Sleep before next check
            time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Error in sync loop: {e}")
            time.sleep(check_interval)


def main():
    """Main entry point - start both web server and sync loop."""
    logger.info("Web configuration daemon starting")
    
    # Start sync loop in background thread
    sync_thread = threading.Thread(target=sync_loop, daemon=True)
    sync_thread.start()
    logger.info("Sync loop thread started")
    
    # Start web server in main thread
    port = 8080
    host = '0.0.0.0'
    local_ip = get_local_ip()
    
    logger.info(f"Web UI starting on http://{local_ip}:{port}")
    print("=" * 60)
    print("COS for Devices - Configuration Web UI")
    print("=" * 60)
    print(f"\nOpen the following URL in your browser:")
    print(f"\n  http://{local_ip}:{port}")
    print(f"\n  (or http://localhost:{port} from this machine)")
    print("\nPress Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # Run Flask app (blocks until stopped)
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Web configuration daemon stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
