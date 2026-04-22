#!/usr/bin/env python3

import os
import subprocess
import sys
import logging.handlers
import time

# Setup logging to journald
logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    handler = logging.handlers.SysLogHandler(address='/dev/log')
    handler.setFormatter(logging.Formatter('rob-cos-demo-configuration.init-confdb-service: %(message)s'))
    logger.addHandler(handler)
except Exception:
    pass

# Configuration mapping: snap config key -> placeholder name
CONFIG_MAPPINGS = {
    "rob-cos-ip": "rob-cos-ip-placeholder",
    "model-name": "model-name-placeholder",
    "robot-uid": "robot-uid-placeholder",
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
    return None


def stop_service():
    """Stop this service."""
    try:
        subprocess.run(
            ["snapctl", "stop", "--disable", "rob-cos-demo-configuration.init-confdb"],
            capture_output=True,
            text=True
        )
        logger.info("Service stopped and disabled successfully")
    except Exception as e:
        logger.warning(f"Failed to disable service: {e}")


def write_config_to_confdb(config_values):
    """Write configuration with real values to confdb.
    
    Args:
        config_values: Dictionary mapping config keys to their values
    """
    defaults_file = os.path.join(
        os.environ.get("SNAP", ""),
        "etc/configuration/defaults/device.yaml"
    )
    
    try:
        # Read default YAML file
        with open(defaults_file, 'r') as f:
            config_data = f.read()
        
        # Replace all placeholders with real values
        for config_key, placeholder in CONFIG_MAPPINGS.items():
            config_data = config_data.replace(placeholder, config_values[config_key])
        
        # Write to confdb
        result = subprocess.run(
            ["snapctl", "set", "--view", ":cos-registration-agent-control-configuration", f"data={config_data}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning(f"Failed to write configuration to confdb: {result.stderr}")
            return False
        else:
            logger.info("Successfully wrote configuration to confdb")
            return True
    except Exception as e:
        logger.error(f"Error writing to confdb: {e}")
        return False


def main():
    """Main service loop."""
    logger.info("Confdb initialization service started")
    
    # Get all snap configuration values
    config_values = {}
    for config_key in CONFIG_MAPPINGS.keys():
        config_values[config_key] = get_snap_config(config_key)
    
    # Check if all required values are set
    missing_values = [key for key, value in config_values.items() if not value]
    
    if missing_values:
        logger.info("Configuration values not all set, disabling service")
        status_parts = [f"{key}: {'set' if config_values[key] else 'not set'}" 
                       for key in CONFIG_MAPPINGS.keys()]
        logger.info(", ".join(status_parts))
        stop_service()
        return
    
    logger.info("All configuration values are set, writing to confdb")
    
    # Retry loop: try to write configuration to confdb
    max_retries = 60  # Max 30 minutes (60 * 30 seconds)
    retry_count = 0
    
    while retry_count < max_retries:
        if write_config_to_confdb(config_values):
            logger.info("Confdb write successful, disabling service")
            stop_service()
            return
        
        retry_count += 1
        logger.warning(f"Confdb write failed, retrying in 30 seconds (attempt {retry_count}/{max_retries})")
        time.sleep(30)
    
    logger.error(f"Failed to write to confdb after {max_retries} attempts, giving up")
    stop_service()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unexpected error in confdb initialization service: {e}")
        sys.exit(1)
