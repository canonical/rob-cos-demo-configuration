#!/usr/bin/env python3
"""
Configuration logic that can be called from both the configure hook and the web UI.
"""

import os
import subprocess
import logging
import logging.handlers


# Configuration mapping: snap config key -> placeholder name
CONFIG_MAPPINGS = {
    "rob-cos-ip": "rob-cos-ip-placeholder",
    "model-name": "model-name-placeholder",
    "robot-uid": "robot-uid-placeholder",
}


def setup_logger(name="configure"):
    """Setup logging to journald."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    try:
        syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
        syslog_formatter = logging.Formatter(f'rob-cos-demo-configuration.{name}: %(message)s')
        syslog_handler.setFormatter(syslog_formatter)
        logger.addHandler(syslog_handler)
    except Exception:
        pass  # Silently fail if syslog unavailable
    
    return logger


def set_confdb_data(config_values, logger=None, update_files=True):
    """
    Set confdb data by replacing placeholders and writing to confdb.
    Uses snapctl which requires hook/service context.
    
    Args:
        config_values: Dictionary mapping config keys to their values
                      (e.g., {"rob-cos-ip": "192.168.1.100", ...})
        logger: Optional logger instance
        update_files: If True, also run search_and_replace.sh to update files
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if logger is None:
        logger = setup_logger()
    
    # Validate that all required configuration values are provided
    missing_values = [key for key in CONFIG_MAPPINGS.keys() if not config_values.get(key)]
    
    if missing_values:
        msg = f"Configuration incomplete. Missing values: {', '.join(missing_values)}"
        logger.info(msg)
        return False, msg
    
    logger.info("All configuration values present, updating confdb")
    
    try:
        # Path to the default configuration file
        defaults_file = os.path.join(
            os.environ.get("SNAP", ""),
            "etc/configuration/defaults/device.yaml"
        )
        
        # Read default YAML file
        with open(defaults_file, 'r') as f:
            config_data = f.read()
        
        # Replace all placeholders with real values
        for config_key, placeholder in CONFIG_MAPPINGS.items():
            if config_key in config_values and config_values[config_key]:
                config_data = config_data.replace(placeholder, config_values[config_key])
        
        # Use snapctl set --view (requires hook/service context)
        result = subprocess.run(
            ["snapctl", "set", "--view", ":cos-registration-agent-control-configuration", f"data={config_data}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            err_msg = f"Failed to write to confdb: {result.stderr}"
            logger.warning(err_msg)
            return False, err_msg
        else:
            logger.info("Configuration updated in confdb")
        
        # Update file-based configuration for content slot consumers
        if update_files:
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
                err_msg = f"Failed to update configuration files: {result.stderr}"
                logger.warning(err_msg)
                return False, err_msg
            else:
                logger.info("Configuration files updated")
        
        return True, "Configuration updated successfully"
        
    except Exception as e:
        err_msg = f"Error updating configuration: {e}"
        logger.error(err_msg)
        return False, err_msg


def get_snap_config_values():
    """
    Get current snap configuration values from snapctl.
    
    Returns:
        Dictionary mapping config keys to their current values
    """
    config_values = {}
    
    for config_key in CONFIG_MAPPINGS.keys():
        try:
            result = subprocess.run(
                ["snapctl", "get", config_key],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                config_values[config_key] = result.stdout.strip()
            else:
                config_values[config_key] = None
        except Exception:
            config_values[config_key] = None
    
    return config_values
