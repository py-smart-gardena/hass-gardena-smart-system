# Home Assistant integration for Gardena Smart System

Custom component to support Gardena Smart System devices.

## About

Originally based on
https://github.com/grm/home-assistant/tree/feature/smart_gardena and
https://github.com/grm/py-smart-gardena

Now uses https://github.com/osks/py-smart-gardena2 instead where
"modelType" support was added.

Added config flow setup, no longer uses configuration.yaml.


## Usage

* Gardena devices are represented as Home Assistant devices, and have
  battery level sensors.

### Installation

TODO: HACS


### Configuration

Setup under Integrations in Home Assistant, search for "Gardena Smart
System".


## TODO

* Only tested with Smart Sensor and Water Control. Need to test with
  Mower, Irrigation Control and Power Socket.

* Add battery

* Make it possible to configure mower duration, smart irrigation
  duration and smart watering duration again.
