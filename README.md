# rob-cos-demo-configuration

This repository hosts a snap for configuring snaps on a device to be monitored with [COS for devices](https://canonical-robotics.readthedocs-hosted.com/en/latest/explanations/observability/what-is-cos-for-robotics/).

It offers two branches with different levels of configuration:

- `basic`: Provides a basic setup to quickly start monitoring and collecting data from a device.
**⚠️ Not production ready - intended only for testing and development.**
- `advanced`: Provides an extended setup with additional features such as TLS, identity management and Ceph storage.

The snap provides a content sharing interface so that other snaps on the device can easily access the configuration.
It exposes a slot called `configuration-read` that allows plugged snaps to read data
stored in `$SNAP_COMMON/configuration`.

More information on how to write a configuration snap for cos for device can be found in the [official documentation](https://canonical-robotics.readthedocs-hosted.com/en/latest/how-to-guides/operation/write-configuration-snap-for-cos-for-robotics/).

## Installation

To install the basic setup:

```
sudo snap install rob-cos-demo-configuration --channel=basic/beta
```

To install the advanced setup:

```
sudo snap install rob-cos-demo-configuration --channel=advanced/beta
```


## Usage:

Once installed connect the snaps on the device requiring the configuration as follows:
```
sudo snap connect rob-cos-snap:configuration-read rob-cos-demo-configuration:configuration-read
```
