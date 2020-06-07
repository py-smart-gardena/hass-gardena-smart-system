[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![hass-gardena-smart-system](https://img.shields.io/github/release/py-smart-gardena/hass-gardena-smart-system.svg?1)](https://github.com/py-smart-gardena/hass-gardena-smart-system)
![Maintenance](https://img.shields.io/maintenance/yes/2020.svg)

{% if prerelease %}
### NB!: This is a Beta version!
{% endif %}

# Home Assistant integration for Gardena Smart System

Custom component to support Gardena Smart System devices.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [About](#about)
- [Installation](#installation)
  - [Installation through HACS](#installation-through-hacs)
  - [Manual installation](#manual-installation)
- [Configuration](#configuration)
  - [Home Assistant](#home-assistant)
  - [Gardena Application Key / Client ID](#gardena-application-key--client-id)
- [Supported devices](#supported-devices)
- [Services](#services)
  - [Smart Irrigation Control services](#smart-irrigation-control-services)
  - [Smart Mower services](#smart-mower-services)
  - [Smart Power Socket services](#smart-power-socket-services)
  - [Smart Sensor services](#smart-sensor-services)
  - [Smart Water Control services](#smart-water-control-services)
- [Changelog](#changelog)
  - [0.1.0](#010)
- [Development](#development)
  - [Debugging](#debugging)
  - [TODO](#todo)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## About

This component is originally based on
https://github.com/grm/home-assistant/tree/feature/smart_gardena and
https://github.com/grm/py-smart-gardena

The integration / component has been changed quite a lot, mainly to
add support for config flow setup and Home Assistant devices. It has
also been cleaned up and some bugs have been fixed. Gardena devices
are now represented as Home Assistant devices, which have battery
level sensors where applicable.

The py-smart-gardena has been forked and is now
https://github.com/osks/py-smart-gardena2 and modelType / model_type
has been added.


## Installation

Requires Home Assistant 0.110 or newer.

### Installation through HACS

If you have not yet installed HACS, go get it at https://hacs.xyz/ and walk through the installation and configuration.

Use "https://github.com/py-smart-gardena/hass-gardena-smart-system" as URL for
a new HACS custom repository.

Then find the Gardena Smart System integration in HACS and install it.

Restart Home Assistant!

Install the new integration through *Configuration -> Integrations* in HA (see below).


### Manual installation

Copy the sub-path `/hass-gardena-smart-system/custom_components/gardena_smart_system` of this repo into the path `/config/custom_components/gardena_smart_system` of your HA installation.

Alternatively use the following commands within an SSH shell into your HA system.
Do NOT try to execute these commands directly your PC on a mounted HA file system. The resulting symlink would be broken for the HA file system.
```
cd /config
git clone https://github.com/py-smart-gardena/hass-gardena-smart-system.git

# if folder custom_components does not yet exist:
mkdir custom_components

cd custom_components
ln -s ../hass-gardena-smart-system/custom_components/gardena_smart_system
```

## Configuration


### Home Assistant

Setup under Integrations in Home Assistant, search for "Gardena Smart
System". You need to enter e-mail, password and your application key / client ID. See below for how to get your Gardena application key.

After setting up the integration, you can adjust some options on the
integration panel for it.

Even though this integration can be installed and configured via the
Home Assistant GUI (uses config flow), you might have to restart Home
Assistant to get it working.


### Gardena Application Key / Client ID

In order to use this integration you must get a client ID /
Application Key from Gardena/Husqvarna.

1. Go to https://developer.husqvarnagroup.cloud/

2. Create an account if needed, otherwise sign in with your Gardena
   account.

3. After signing in you will be automatically redirected to "Your
   applications". (Otherwise go to: https://developer.husqvarnagroup.cloud/apps)

4. Create an new application, name it for example "My Home Assistant"
   (doesn't matter), leave the other fields empty.

5. Click on "+Connect new API" and connect the Authentication API and
   the GARDENA smart system API.

6. Copy your Application Key, this is what you need when you add the integration in Home Assistant.


## Supported devices

The following devices are supported but not all of them have been tested.

* Gardena Smart Irrigation Control (as switch)
* Gardena Smart Mower (as vacuum)
* Gardena Smart Sensor (as sensor)
* Gardena Smart Water Control (as switch)
* Gardena Smart Power Socket (as switch)

## Services

### Smart Irrigation Control services

> [TODO: document services]

### Smart Mower services

`vacuum.start`
Start the mower using the Gardena API command START_SECONDS_TO_OVERRIDE.
The mower switches to manual operation for a defined duration of time.   The duration is taken from the integration option "*Mower Duration (minutes)*" (see *Configuration -> Integrations* in HA).

`vacuum.stop`
Stop the mower using the Gardena API command PARK_UNTIL_FURTHER_NOTICE.
The mower cancels the current operation, returns to charging station and ignores schedule.

`vacuum.return_to_base`
Stop the mower using Gardena API command PARK_UNTIL_NEXT_TASK.
The mower cancels the current operation and returns to charging station. It will reactivate with the next schedule.

### Smart Power Socket services

> [TODO: document services]

### Smart Sensor services

> [TODO: document services]

### Smart Water Control services

> [TODO: document services]

## Changelog

### 0.1.0
- First release with a version number
- Bump py-smart-gardena to 0.7.4
- Connection stability has been improved from updating py-smart-gardena
- A binary_sensor has been added which holds the websocket connection status (its status goes offline a few seconds from time to time when the access token expires while the access token is refreshed)

## Development

### Debugging

To enable debug logging for this integration and related libraries you
can control this in your Home Assistant `configuration.yaml`
file. Example:

```
logger:
  default: info
  logs:
    custom_components.gardena_smart_system: debug
    custom_components.gardena_smart_system.mower : debug
    custom_components.gardena_smart_system.sensor : debug
    custom_components.gardena_smart_system.switch : debug
    custom_components.gardena_smart_system.config_flow : debug

    gardena: debug
    gardena.smart_system: debug
    websocket: debug
```

After a restart detailed log entries will appear in `/config/home-assistant.log`.

### TODO

* Do we need support for more than one location? Should we make it
  possible to configure it?
