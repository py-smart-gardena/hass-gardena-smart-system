## TOC

- [Watering the lawn based on the current soil moisture and time of day. With the aim that the lawn is watered sufficiently but is not too wet.](##watering-the-lawn-based-on-the-current-soil-moisture-and-time-of-day-with-the-aim-that-the-lawn-is-watered-sufficiently-but-is-not-too-wet)
- [Notification over HomeAssistant Companion App or as Telegram Messenger message or over Amazon Alexa with the help of Alexa Media Player Integration](#notification-over-homeassistant-companion-app-or-as-telegram-messenger-message-or-over-amazon-alexa-with-the-help-of-alexa-media-player-integration)
- [Use a NFC tag to start and stop mowing](#use-a-nfc-tag-to-start-and-stop-mowing)

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
## Use a NFC tag to start and stop mowing

Normaly my Gardena Irrigation Control works per automations, but in a part of situations i have to start/stop it manualy (i.e. I will fill a pot with water) in this cases i have before use my Smartphone open the App search for the Watercontroll entity and start/stop this. 

Now with the [NFC tag integration](https://companion.home-assistant.io/docs/integrations/universal-links/) from HomeAssistant thats is more easy than befor, now i’m scan with my Smartphone an tag on my Hose trolley and give the okay that the tag starts the HA App and the water control starts if it's off and stopps if it's on.

Steps for this.

1. Buy an NFC tag like this one [https://www.amazon.de/dp/B06Y1BLLD4?ref=ppx_pop_mob_ap_share](https://www.amazon.de/dp/B06Y1BLLD4?ref=ppx_pop_mob_ap_share)

2. Install the [HA Companion App](https://companion.home-assistant.io/) on your Smartphone (if you have't do this before)

3. [Write the NFC tag with the HA App](https://companion.home-assistant.io/docs/integrations/universal-links/)
![28CB9BFE-3F41-4D96-91EA-34D6EEA1A0CF](https://user-images.githubusercontent.com/36472486/93881822-b272dc80-fcdf-11ea-9d6a-8d615b4b58d2.jpeg)

![1F0AF2E9-4E1B-4634-BB39-9C9A173125BD](https://user-images.githubusercontent.com/36472486/93881365-19dc5c80-fcdf-11ea-9f7c-51e51d0533c1.jpeg)
![6BA84B75-05BE-4730-8C35-BF274F7E2A82](https://user-images.githubusercontent.com/36472486/93881368-19dc5c80-fcdf-11ea-8264-645fa00ebccc.jpeg)
![217C9CD3-4F58-48DD-A7FB-EB1211C11F29](https://user-images.githubusercontent.com/36472486/93881369-1a74f300-fcdf-11ea-901c-d9f61b576185.png)
![F53B6C62-1910-4871-A54F-FDA875E09B78](https://user-images.githubusercontent.com/36472486/93881370-1a74f300-fcdf-11ea-86e7-fa65dfaadbd0.png)
![0E495C12-8DF9-4B79-8681-D9842C73815C](https://user-images.githubusercontent.com/36472486/93881371-1b0d8980-fcdf-11ea-8418-28134a1e9850.jpeg)

4. Go to the [NFC tag configuration in HA](https://www.home-assistant.io/blog/2020/09/15/home-assistant-tags/) and give your NFC tag an readable name and create an Automation like this on

![1B9A0B40-1FF8-4B37-8D69-1BA737A097EA](https://user-images.githubusercontent.com/36472486/93882213-2dd48e00-fce0-11ea-8c3a-d1a85f7e5800.jpeg)
![CEFDA1D6-094A-4C3F-AB9F-06465707CAFF](https://user-images.githubusercontent.com/36472486/93879140-7e95b800-fcdb-11ea-8076-61d9b694cb3f.jpeg)
![2C4047E5-7F17-4CF5-8D06-83361184C914](https://user-images.githubusercontent.com/36472486/93879146-7fc6e500-fcdb-11ea-828c-fd3bb97c6e8a.jpeg)
![7F8A4DEA-49BA-4557-865D-7582D5E67C26](https://user-images.githubusercontent.com/36472486/93879150-80f81200-fcdb-11ea-8c0b-d32e133c27de.jpeg)
![F2278990-D81C-4A01-86A9-8D85F9C95032](https://user-images.githubusercontent.com/36472486/93879153-8190a880-fcdb-11ea-9145-dcb31f433766.jpeg)
![6CF720DC-4F9B-4B20-B1EF-DF169F405CE9](https://user-images.githubusercontent.com/36472486/93879154-82293f00-fcdb-11ea-807f-c030c79cb4db.png)
![70A2AC60-AFFC-467C-B294-A0A93D253DBE](https://user-images.githubusercontent.com/36472486/93879155-835a6c00-fcdb-11ea-9188-ddc51f44dbf5.png)

```
##########################################################################
# Control Watercontrol with NFC tag
##########################################################################

- id: '1600768999472'
  alias: 'NFC Tag Garden watering on/off is scanned if water is off'
  description: If the irrigation in the garden is off start watering
  trigger:
  - platform: tag
    tag_id: 9dc6d5b1-651d-4880-839c-19cdd798a5f8
  condition:
  - condition: device
    type: is_off
    device_id: eecdf62964f3494d877413f7bd7b2a45
    entity_id: switch.garten_water_control
    domain: switch
  action:
  - type: turn_on
    device_id: eecdf62964f3494d877413f7bd7b2a45
    entity_id: switch.garten_water_control
    domain: switch
  mode: single

- id: '1600769207834'
  alias: 'NFC Tag Garden watering on/off is scanned if water is on'
  description: If the irrigation in the garden is on stop watering
  trigger:
  - platform: tag
    tag_id: 9dc6d5b1-651d-4880-839c-19cdd798a5f8
  condition:
  - condition: device
    type: is_on
    device_id: eecdf62964f3494d877413f7bd7b2a45
    entity_id: switch.garten_water_control
    domain: switch
  action:
  - type: turn_off
    device_id: eecdf62964f3494d877413f7bd7b2a45
    entity_id: switch.garten_water_control
    domain: switch
  mode: single```


