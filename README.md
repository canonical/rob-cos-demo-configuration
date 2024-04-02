# rob-cos-demo-configuration

A snap for configuring the rob cos snaps on the device.
    
This snap offers a default configuration for a rob cos device. 
It also offers a content sharing interface, to allow snaps on a device that is meant
to work with the rob-cos ecosystem to easily get configured.

It offers a slot called configuration-read that allows plugged snaps to read data
stored in $SNAP_COMMON/configuration.

Usage:

Connect as follows:
```
sudo snap connect rob-cos-snap:configuration-read rob-cos-demo-configuration:configuration-read
```

