# Home Assistant integration for Gardena Smart System

Custom component to support Gardena Smart System devices.

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


### Installation

Requires Home Assistant 0.110 or newer.

#### HACS

https://hacs.xyz/

Use "https://github.com/osks/hass-gardena-smart-system" as URL for
custom repository.

Even though this integration can be installed and configured via the
Home Assistant GUI (uses config flow), you might have to restart Home
Assistant to get it working.


#### Manual custom component

```
cd <path>/<to>/<your>/<config>
git clone https://github.com/osks/hass-gardena-smart-system.git
mkdir custom_components (if not exist)
cd custom_components
ln -s ../hass-gardena-smart-system/custom_components/gardena_smart_system
```

### Configuration


#### Home Assistant

Setup under Integrations in Home Assistant, search for "Gardena Smart
System". You need to enter e-mail, password and client ID (also called
application key). See below for how to get your Gardena client ID.

After setting up the integration, you can adjust some options on the
integration panel for it.


#### Gardena Client ID / Application Key

In order to use this integration you must get a client ID /
Application Key from Gardena.

1. Go to https://developer.1689.cloud/

2. Create an account if needed, otherwise sign in with your Gardena
   account.

3. After singing in you will be automatically redirected to "Your
   applications". (Otherwise go to https://developer.1689.cloud/apps)

4. Create an new application, name it for example "My Home Assistant"
   (doesn't matter), leave the other fields empty.

5. Click on "Connect new API" and connect the Authentication API and
   the GARDENA smart system API.

6. Copy your Application Key, this is your Client ID.


## Supported devices

The following devices are supported but not all of them have been tested.

* Gardena Smart Mower (as vacuum) (not tested)
* Gardena Smart Sensor (as sensor) (tested)
* Gardena Smart Water Control (as switch) (tested)
* Gardena Smart Irrigation Control (as switch) (not tested)
* Gardena Smart Power Socket (as switch) (not tested)


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


### TODO

* Only tested with Smart Sensor and Water Control. Need to test with
  Mower, Irrigation Control and Power Socket.

* Do we need support for more than one location? Should we make it
  possible to configure it?
