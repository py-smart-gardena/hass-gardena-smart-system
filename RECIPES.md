## TOC

- [Watering the lawn based on the current soil moisture and time of day. With the aim that the lawn is watered sufficiently but is not too wet.](##watering-the-lawn-based-on-the-current-soil-moisture-and-time-of-day-with-the-aim-that-the-lawn-is-watered-sufficiently-but-is-not-too-wet)
- [Notification over HomeAssistant Companion App or as Telegram Messenger message or over Amazon Alexa with the help of Alexa Media Player Integration](#notification-over-homeassistant-companion-app-or-as-telegram-messenger-message-or-over-amazon-alexa-with-the-help-of-alexa-media-player-integration)

## Watering the lawn based on the current soil moisture and time of day. With the aim that the lawn is watered sufficiently but is not too wet.

### Why not with the Gardena App:
The problem of Gardena automation for lawn irrigation is that this ...

1. not flexible enough for soil moisture
2. not dynamic enough
3. Lawn gets too wet
4. Water consumption is too high

### Requirements
- Installed [hass-gardena-smart-system](https://github.com/py-smart-gardena/hass-gardena-smart-system/) integration
- Timer with the need of long-time availability (with HA restart in the between)
   ->https://community.home-assistant.io/t/how-to-make-active-timers-survive-a-restart/146248
- [Gardena smart control](https://www.gardena.com/de/produkte/bewasserung/bewasserungssteuerung/smart-water-control/967045101/)
- [Gardena Smart Sensor](https://www.gardena.com/de/produkte/bewasserung/bewasserungssteuerung/smart-sensor/967044801/) or other sensors for depending values
- [Gardena Pipeline System](https://www.gardena.com/de/produkte/bewasserung/pipelines/)

### Automation example:

```yaml
- id: lawn_irrigation_garden
  alias: lawn irrigation garden
  trigger:
    platform: time_pattern
    minutes: '/15'
    seconds: 0
  condition:
    condition: and
    conditions:
     - condition: state
       entity_id: timer.lawn_irrigation_garden
       state: 'idle'
     - condition: numeric_state
       entity_id: sensor.garden_sensor_light_intensity
       below: 10
     - condition: numeric_state
       entity_id: sensor.plant bed_sensor_light_intensity
       below: 10
     - condition: numeric_state
       entity_id: sensor.garden_sensor_ambient_temperature
       above: 5
     - condition: numeric_state
       entity_id: sensor.garden_sensor_soil_humidity
       below: 10
  action:
    - service: timer.start
      entity_id: timer.timer.lawn_irrigation_garden
    - service: switch.turn_on
      entity_id: switch.garden_water_control
    - delay: 0:12:00 
    - service: switch.turn_off
      entity_id: switch.garden_water_control
    - delay: 0:60:00 
    - service: switch.turn_on
      entity_id: switch.garden_water_control
    - delay: 0:24:00
    - service: switch.turn_off
      entity_id: switch.garden_water_control
    - delay: 0:60:00
    - service: switch.turn_on
      entity_id: switch.garden_water_control
    - delay: 0:24:00
    - service: switch.turn_off 
```

## Notification over [HomeAssistant Companion App](https://companion.home-assistant.io/) or as [Telegram Messenger](https://www.home-assistant.io/integrations/telegram/) message or over [Amazon Alexa with the help of Alexa Media Player Integration](https://github.com/custom-components/alexa_media_player)

### Why not with the Gardena App:
It is not possible to get Messages from the status of the [smart water](https://www.gardena.com/de/produkte/bewasserung/bewasserungssteuerung/smart-water-control/967045101/) or the [sensor](https://www.gardena.com/de/produkte/bewasserung/bewasserungssteuerung/smart-sensor/967044801/) devices.

It is not possible to get this notifications over Amazon Alexa from the App

### Requirements

1. Installed hass-gardena-smart-system integration
2. [Home Assistant Compagnion iOS or Android App](https://companion.home-assistant.io/)
3. [Gardena smart control](https://www.gardena.com/de/produkte/bewasserung/bewasserungssteuerung/smart-water-control/967045101/)
4. [Gardena Smart Sensor](https://www.gardena.com/de/produkte/bewasserung/bewasserungssteuerung/smart-sensor/967044801/) or other sensors for depending values
5. [Gardena Pipeline System](https://www.gardena.com/de/produkte/bewasserung/pipelines/)
6. (optional) [Telegram Messenger Integration](https://www.home-assistant.io/integrations/telegram/)
7. (optional) [Alexa Media Player Integration](https://github.com/custom-components/alexa_media_player) you can find and install this Integration over HACS 

### Configuration:
only needed for Telegram
```yaml
- alias: "Notify lawn irrigation garden on"
  trigger:
    platform: state
    entity_id: switch.garden_water_control
    to: 'on'
  action:
    - service: notify.notify
      data:
        title: "lawn irrigation"
        message: "Watering in the garden has started"
    - service: notify.alexa_media
      data:
        data:
          type: announce
        target: 
          - media_player.radio_livingroom
        message: "Watering in the garden has started. The humidity is currently {{ states.sensor.garden_sensor_humidity.state }}% the temperature is now {{ states.sensor.garden_sensor_temperature.state }}°C"
    - service: notify.telegram_[you Telegram channel]
      data_template:
        title: '*Watering in the garden has started!*'
        message: "Watering in the garden has started. The humidity is currently {{ states.sensor.garden_sensor_humidity.state }}% the temperature is now {{ states.sensor.garden_sensor_temperature.state }}°C -> https://[public HA URL]/lovelace/terrasse"
        data:
            inline_keyboard:
            - 'Stop watering:/stopwateringgarden'
            - ' Stop for 3 hours:/stopwateringgarden3h, Stop for 24 hours:/stopwateringgarden24h'
          
- id: 'telegram_stop_watering_garden'
  alias: 'Telegram Stop watering garden'
  
  trigger:
    platform: event
    event_type: telegram_callback
    event_data:
      data: '/stopwateringgarden'
  action:
  - service: telegram_bot.answer_callback_query
    data_template:
      callback_query_id: '{{ trigger.event.data.id }}'
      message: 'OK, I'll stop watering the garden'
  - service: switch.turn_off
    entity_id: switch.garden_water_control
  - service: notify.telegram_[you Telegram channel]
    data_template:
      title: '*Watering garden!*'
      message: "Watering stopped in the garden https://[public HA URL]/lovelace/terrasse"

- id: 'telegram_stop_watering_garden_3h'
  alias: 'Telegram watering stop 3h'
  trigger:
    platform: event
    event_type: telegram_callback
    event_data:
      data: '/stopwateringgarden3h'
  action:
  - service: telegram_bot.answer_callback_query
    data_template:
      callback_query_id: '{{ trigger.event.data.id }}'
      message: 'OK, stop watering for 3 hours'
  - service: automation.turn_off
    entity_id: automation.lawn_irrigation_garden
  - service: notify.telegram_[you Telegram channel]
    data_template:
      title: '*Watering Garden!*'
      message: "Irrigation in the garden interrupted for 3 hours https://[public HA URL]/lovelace/terrasse"
  - delay: '03:00:00'
  - service: automation.turn_on
    entity_id: automation.lawn_irrigation_garden
  - service: notify.telegram_[you Telegram channel]
    data_template:
      title: '*Watering Garden!*'
      message: "Automation for irrigation in the garden was restarted after 3 hours https://[public HA URL]/lovelace/terrasse"

- id: 'telegram_stop_watering_garden_24h'
  alias: 'Telegram watering stop 24h'
  trigger:
    platform: event
    event_type: telegram_callback
    event_data:
      data: '/stopwateringgarden24h'
  action:
  - service: telegram_bot.answer_callback_query
    data_template:
      callback_query_id: '{{ trigger.event.data.id }}'
      message: 'OK, stop watering for 24 hours'
  - service: automation.turn_off
    entity_id: automation.lawn_irrigation_garden
  - service: notify.telegram_[you Telegram channel]
    data_template:
      title: '*Watering Garden!*'
      message: "OK, stop watering for 24 hours https://[public HA URL]/lovelace/terrasse"
  - delay: '24:00:00'
  - service: automation.turn_on
    entity_id: automation.lawn_irrigation_garden
  - service: notify.telegram_[you Telegram channel]
    data_template:
      title: '*Watering Garden!*'
      message: "Automation for irrigation in the garden was restarted after 24 hours https://[public HA URL]/lovelace/terrasse"

- alias: "Notify watering Garden off"
  trigger:
    platform: state
    entity_id: switch.garden_water_control
    to: 'off'
  action:
    - service: notify.notify
      data:
        title: "Watering Garden"
        message: "Watering in the garden has ended"      
   - service: notify.alexa_media
      data:
        data:
          type: announce
        target: 
          - media_player.radio_wohnzimmer
        message: "Watering in the garden has ended. The humidity is now {{ states.sensor.garden_sensor_humidity.state }}%"
    - service: notify.telegram_[you Telegram channel]
      data_template:
        title: '*Watering in the garden has ended!*'
        message: "Watering in the garden has ended. The humidity is now {{ states.sensor.garden_sensor_humidity.state }}% -> https://[public HA URL]/lovelace/terrasse"
```
