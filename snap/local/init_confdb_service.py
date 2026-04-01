#!/usr/bin/env python3
"""
Confdb initialization service - one-shot.
Checks snap config and writes to confdb once, then disables itself.
Started by hooks when interface connects.
"""

import os
import subprocess
import sys
import time
import logging.handlers

# Add snap lib to Python path
snap_dir = os.environ.get("SNAP", "")
if snap_dir:
    sys.path.insert(0, os.path.join(snap_dir, "usr/lib"))

from configure_logic import CONFIG_MAPPINGS, get_snap_config_values, setup_logger

# Setup logging
logger = setup_logger("init-confdb-service")


def stop_service():
    """Stop and disable this service."""
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
    """
    Write configuration with real values to confdb.
    
    Args:
        config_values: Dictionary mapping config keys to their values
        
    Returns:
        True if successful, False otherwise
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
            
            # Also update file-based configuration for content slot
            search_replace_script = os.path.join(
                os.environ.get("SNAP", ""),
                "usr/bin/search_and_replace.sh"
            )
            
            result = subprocess.run(
                [search_replace_script],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning(f"Failed to update configuration files: {result.stderr}")
            else:
                logger.info("Configuration files updated")
            
            return True
    except Exception as e:
        logger.error(f"Error writing to confdb: {e}")
        return False


def main():
    """Main service - one-shot execution."""
    logger.info("Confdb initialization service started")
    
    # Get all snap configuration values
    config_values = get_snap_config_values()
    
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
