[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![hass-gardena-smart-system](https://img.shields.io/github/release/py-smart-gardena/hass-gardena-smart-system.svg?1)](https://github.com/py-smart-gardena/hass-gardena-smart-system)
![Maintenance](https://img.shields.io/maintenance/yes/2020.svg)

{% if prerelease %}
### NB!: This is a Beta version!
{% endif %}

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![hass-gardena-smart-system](https://img.shields.io/github/release/py-smart-gardena/hass-gardena-smart-system.svg?1)](https://github.com/py-smart-gardena/hass-gardena-smart-system)

Feel free to join the discord server : [![Support Server](https://img.shields.io/discord/853252789522268180.svg?color=7289da&label=Discord&logo=discord&style=flat-square)](https://discord.gg/59sFjykS)

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
  - [Gardena Application Key / Client ID and Application secret / client secret](#gardena-application-key--client-id-and-application-secret--client-secret)
- [Supported devices](#supported-devices)
- [Services](#services)
  - [Smart Irrigation Control services](#smart-irrigation-control-services)
  - [Smart Mower services](#smart-mower-services)
  - [Smart Power Socket services](#smart-power-socket-services)
  - [Smart Sensor services](#smart-sensor-services)
  - [Smart Water Control services](#smart-water-control-services)
- [Recipes](#recipes)
- [Development](#development)
  - [Debugging](#debugging)
- [Changelog](#changelog)
  - [1.0.0b5](#100b5)
  - [0.2.1](#021)
  - [0.2.0](#020)
  - [0.1.0](#010)
- [Development](#development-1)
  - [Debugging](#debugging-1)
  - [TODO](#todo)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

> :warning: **Starting from version 1.0.0b5: You might probably have to uninstall and reinstall the integration as credentials requirements and method has changed. THERE IS A BREAKING CHANGE IN THE CONFIGURATION DUE TO AN UPDATE ON THE GARDENA API**


## About

This component is originally based on
https://github.com/grm/home-assistant/tree/feature/smart_gardena and
https://github.com/grm/py-smart-gardena

The integration / component has been changed quite a lot, mainly to
add support for config flow setup and Home Assistant devices. It has
also been cleaned up and some bugs have been fixed. Gardena devices
are now represented as Home Assistant devices, which have battery
level sensors where applicable.

**This project needs your support.**  
Gardena equipments are expensive, and I need to buy them in order to add support.
If you find this library useful and want to help me support more devices (or if you
just want to reward me for my spent time), you are very welcome !   
Your help is very much appreciated.

Here are the links if you want to show your support :  
<span class="badge-paypal"><a href="https://paypal.me/grmklein" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-yellow.svg" alt="PayPal donate button" /></a></span>

## Installation

Requires Home Assistant 0.115.0 or newer.

### Installation through HACS

If you have not yet installed HACS, go get it at https://hacs.xyz/ and walk through the installation and configuration.

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
System". You need to enter your application key / client ID and your applications secret / client secret. See below for how to get your Gardena application key and secret.

After setting up the integration, you can adjust some options on the
integration panel for it.

Even though this integration can be installed and configured via the
Home Assistant GUI (uses config flow), you might have to restart Home
Assistant to get it working.


### Gardena Application Key / Client ID and Application secret / client secret

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

6. Copy your Application Key and Application secret, this is what you need when you add the integration in Home Assistant.


## Supported devices

The following devices are supported :

* Gardena Smart Irrigation Control (as switch)
* Gardena Smart Mower (as lawn_mower)
* Gardena Smart Sensor (as sensor)
* Gardena Smart Water Control (as switch)
* Gardena Smart Power Socket (as switch)

## Services

### Smart Irrigation Control services

> [TODO: document services]

### Smart Mower services

`lawn_mower.start_mowing`  
Start the mower using the Gardena API command START_DONT_OVERRIDE.  
The mower resumes the schedule.

`lawn_mower.pause`  
Stop the mower using the Gardena API command PARK_UNTIL_FURTHER_NOTICE.  
The mower cancels the current operation, returns to charging station and ignores schedule.

`lawn_mower.dock`  
Stop the mower using Gardena API command PARK_UNTIL_NEXT_TASK.  
The mower cancels the current operation and returns to charging station. It will reactivate with the next schedule.

### Smart Power Socket services

> [TODO: document services]

### Smart Sensor services

> [TODO: document services]

### Smart Water Control services

> [TODO: document services]

## Recipes

Some recipes were made by the community.
You can find them [here](RECIPES.md).

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

## Changelog

### 1.0.0b5
- Update credentials requirements : the integration need to be completely removed from home assistant and resintalled

### 0.2.1
- Correct a bug with some mowers where the wrong id was chosen
- Correct a bug with the water pump where the wrong id was chosen

### 0.2.0
- Integration to default repositories of HACS
- Rename vaccum attributes for mower as described :
  Two attributes added. Both are compiled from existing attributes:
  * `error code` contains NONE if there is no error and the code from `last error code` if an error is active.
  * `status code` contains a copy of `activity` as long as there is no error and a copy of `error code` if an error
    is active. This corresponds to the state in the old integration of Wijnand.
  * Attribute names changed: last_error_code -> last_error, error_code -> error, status_code -> state
  * Const ATTR_LAST_ERROR_CODE removed, not used any more.

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
