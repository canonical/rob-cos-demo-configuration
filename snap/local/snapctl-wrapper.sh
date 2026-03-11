#!/bin/sh -e
# Wrapper script to execute snapctl commands from integration tests
# Usage: snapctl-wrapper.sh <snapctl-args...>

# Execute the snapctl command with all passed arguments
exec snapctl "$@"
