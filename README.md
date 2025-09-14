[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

![Icon](https://github.com/jmcollin78/solar_optimizer/blob/main/images/icon.png?raw=true)

> ![Tip](https://github.com/jmcollin78/solar_optimizer/blob/main/images/tips.png?raw=true) This integration allows you to optimize the use of your solar energy. It controls the switching on and off of your equipment, the activation of which is deferred over time depending on production and current electricity consumption.

- [What is Solar Optimizer?](#what-is-solar-optimizer)
- [How does it work?](#how-does-it-work)
  - [Anti-flickering](#anti-flickering)
  - [Usability](#usability)
  - [Device Prioritization](#device-prioritization)
- [Installation](#installation)
  - [Migration Procedure from Version 2.x to 3.x](#migration-procedure-from-version-2x-to-3x)
  - [HACS installation (recommended)](#hacs-installation-recommended)
  - [Manual Install](#manual-install)
- [The configuration](#the-configuration)
  - [Configure the Integration for the First Time](#configure-the-integration-for-the-first-time)
  - [Configure the Devices](#configure-the-devices)
    - [Configuring a Simple Device (On/Off)](#configuring-a-simple-device-onoff)
  - [Configuring a Device with Variable Power](#configuring-a-device-with-variable-power)
  - [Configuration Examples](#configuration-examples)
    - [Controlling Tesla Charging](#controlling-tesla-charging)
    - [Controlling an Air Conditioner hvac mode](#controlling-an-air-conditioner-hvac-mode)
    - [Controlling an Air Conditioner preset](#controlling-an-air-conditioner-preset)
    - [Controlling a Dehumidifier](#controlling-a-dehumidifier)
    - [Control for a Light](#control-for-a-light)
- [Available Entities](#available-entities)
  - [The "configuration" Device](#the-configuration-device)
  - [Devices and Their Entities](#devices-and-their-entities)
    - [Switch Attributes](#switch-attributes)
- [Priority Management](#priority-management)
  - [Priority Weight](#priority-weight)
  - [Device Priority](#device-priority)
- [Events](#events)
- [Actions](#actions)
  - [reset\_on\_time](#reset_on_time)
- [Creating Sensor Templates for Your Installation](#creating-sensor-templates-for-your-installation)
    - [File `configuration.yaml`:](#file-configurationyaml)
    - [File `templates.yaml`:](#file-templatesyaml)
- [A Card for Your Dashboards as a complement](#a-card-for-your-dashboards-as-a-complement)
  - [Install the Plugins](#install-the-plugins)
  - [Install the Templates](#install-the-templates)
  - [Add a Card for Each Device](#add-a-card-for-each-device)
  - [Using the Card](#using-the-card)
    - [Icon Color](#icon-color)
    - [Badge](#badge)
    - [Actions on the Card](#actions-on-the-card)
- [Contributions are welcome!](#contributions-are-welcome)


>![New](https://github.com/jmcollin78/solar_optimizer/blob/main/images/new-icon.png?raw=true) _*News*_
> * **release 3.5.0**:
>   - added support for priority management. See [Priority Management](#priority-management)
> * **release 3.2.0** :
> - Added an optional sensor for the net instantaneous power charged or discharged in the battery. This value is added to the net consumed power. Since the battery charging power affects the power available for the devices, it is taken into account. The sensor must report a value in watts, positive when the battery is discharging and negative when the battery is charging.
> * **release 3.0.0** :
> - Added a configuration UI for devices.
> - ⚠️ Installing release 3.0.0 requires a specific procedure. See the migration procedure below [here](#migration-procedure-from-version-2x-to-3x).
> * **release 2.1.0** :
> - added a minimum duration of ignition during off-peak hours. Allows you to manage equipment that must have a minimum of ignition per day such as water heaters or chargers (cars, battery, ...). If the sunshine has not reached the required duration, then the equipment will turn on during off-peak hours. You can also define at what time the ignition counters are reset to zero, which allows you to take advantage of all off-peak hours
> * **release 2.0.0** :
> - added a device per controlled equipment to group the entities,
> - added an ignition time counter for each device. When the controlled switch goes to 'Off', the time counter is incremented by the time spent 'On', in seconds. This counter is reset to zero every day at midnight.
> - added a maximum time to 'On' in the configuration (in minutes). When this duration is exceeded, the equipment is no longer usable by the algorithm (is_usable = off) until the next reset. This offers the possibility of not exceeding a maximum ignition time per day, even when solar power is available.
> - to take advantage of this new information, don't forget to update the decluterring template (at the end of this file)
> - this release opens the door to more significant developments based on the ignition time (having a daily minimum for example) and prepares the ground for the arrival of the configuration via the graphical interface.

# What is Solar Optimizer?
This integration will allow you to maximize the use of your solar production. You delegate to it the control of your equipment whose activation can be deferred over time (water heater, swimming pool pump, electric vehicle charge, dishwasher, washing machine, etc.) and it takes care of launching them when the power produced is sufficient.

It constantly tries to minimize the import and export of energy by starting, stopping and modifying the power allocated to equipment.

2 types of equipment are managed:
1. equipment controlled by a switch (a service in general) which has a fixed and pre-determined power consumption,
2. equipment whose power consumption is adjustable (Tesla, Robotdyn). By adjusting the power allocated to this equipment, Solar Optimizer aligns consumption as closely as possible with production.

The ideal is to have at least one piece of equipment whose power is adjustable in the list of equipment managed by Solar Optimizer.

# How does it work?
The operation is as follows:
1. at regular intervals (configurable), the algorithm simulates modifications to the states of the equipment (on / off / allocated power) and calculates a cost for this configuration. Overall the cost is the `a * imported_power + b * exported_power`. The coefficients a and b are calculated according to the cost of electricity at the time of calculation,
2. the algorithm keeps the best configuration (the one with a minimum cost) and looks for other solutions, until a minimum is reached.
3. the best configuration is then applied.

The algorithm used is a simulated annealing type algorithm, a description of which you will find here: https://fr.wikipedia.org/wiki/Recuit_simul%C3%A9

## Anti-flickering
To avoid the effects of flickering from one cycle to another, a minimum activation delay can be configured by equipment: `duration_min`. For example: a water heater must be activated for at least one hour for the ignition to be useful, charging an electric car must last at least two hours, ...
Similarly, a minimum stop duration can be specified in the `duration_stop_min` parameter.

## Usability
Each configured device is associated with a switch-type entity named `enable` that authorizes the algorithm to use the device. If I want to force the heating of the hot water tank, I put its switch to off. The algorithm will therefore not look at it, the water heater switches back to manual, not managed by Solar Optimizer.

In addition, it is possible to define a usability rule for equipment. For example, if the car is charged at more than 90%, the algorithm considers that the equipment which controls the charging of the car must be switched off. This rule is defined in the form of a configurable template which is True if the equipment is usable.

If a battery is specified when configuring the integration and if the threshold `battery_soc_threshold` is specified, the equipment will only be usable if the soc (percentage of battery charge) is greater than or equal to the threshold.

A maximum daily usage time is optionally configurable. If it is valued and if the duration of use of the equipment is exceeded, then the equipment will not be usable by the algorithm and therefore leaves power for other equipment.

A minimum daily usage time is also optionally configurable. This parameter ensures that the equipment will be on for a certain minimum duration. You specify at what time the off-peak hours start (`offpeak_time`) and the minimum duration in minutes (`min_on_time_per_day_min`). If at the time indicated by `offpeak_time`, the minimum activation duration has not been reached, then the equipment is activated until the change of day (configurable in the integration and 05:00 by default) or until the maximum usage is reached (`max_on_time_per_day_min`) or during all the off-peak hours if `max_on_time_per_day_min` is not set. This ensures that the water heater or the car will be charged the next morning even if the solar production has not allowed the device to be recharged. It is up to you to invent the uses of this function.

These 5 rules allow the algorithm to only order what is really useful at a time t. These rules are re-evaluated at each cycle.

## Device Prioritization
Priority management is described [here](#priority-management).

## Setting Purchase and Resale Costs
The behavior of the algorithm is strongly influenced by the values of the sensors **"imported kWh cost"** and **"exported kWh cost"**.
The algorithm calculates the *"fictitious cost"* of a combination of on/off states and desired power levels for the controlled devices.

If these two values are equal, then the cost of importing 500 W from the grid will be the same as the cost of exporting 500 W to the grid.
Therefore, SO can either reject the 500 W (under-consumption) or import 500 W (over-consumption), as long as production allows.

The values of the purchase and resale cost sensors should be set as follows:

1. **If they are equal** → SO will accept import and export equally. For SO, it “costs” the same to export 500 W as to import 500 W.
2. **If purchase cost >> resale cost** → SO will minimize import but may export more (energy lost).
3. **If resale cost >> purchase cost** → the opposite happens: SO will minimize export and potentially import more (thus increasing the bill).

👉 If you want to avoid any import (i.e., buying from the grid): set the purchase cost **much higher** than the resale cost.

👉 For those with self-consumption contracts without resale: everything rejected is lost. In this case, you may want to minimize rejections, even if it means importing a bit more. For this configuration, set resale cost **much higher** than purchase cost.

On my side, I set the actual purchase costs (which vary depending on the day and time: Tempo contract) and the real resale cost of 13 cts/kWh.
So, if my purchase cost is low (off-peak blue hours), I can import more.
If the purchase cost is very high (peak red hours), I won’t import at all. That’s exactly what I want in my case — but that’s specific to me and because I have a resale contract at 13 cts/kWh.

**⚠️ WARNING:** Costs must not be zero!

# Installation

## Migration Procedure from Version 2.x to 3.x

Version 3.0.0 introduces a configuration UI that allows for easy addition and modification of controlled devices.

This procedure should only be followed if you have already installed and configured a 2.x version.

Installing v3.0.0 requires recreating all devices through the UI and removing the configuration from the `configuration.yaml` file. Follow these steps carefully:

1. Go to *Settings / Integration*, select "Solar Optimizer," and remove the "Solar Optimizer" device. The "Solar Optimizer" integration should no longer be visible.
2. Remove the configuration from your `configuration.yaml` file.
3. Open HACS, search for "Solar Optimizer," and install version 3.0.0.
4. Go to *Settings / Integration*, click on "Add Integration," and select "Solar Optimizer."
5. You will arrive at the common parameter configuration page, described [here](#configure-the-integration-for-the-first-time).

## HACS installation (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jmcollin78&repository=solar_optimizer&category=integration)

1. Install [HACS](https://hacs.xyz/). This way you get updates automatically.
2. Add this Github repo as a custom repo in HACS settings.
3. Find and install "Solar Optimizer" in HACS and click "Install".
4. Restart Home Assistant.
5. Then you can add the Solar Optimizer integration in the integration page. You can only install one Solar Optimizer integration.

## Manual Install
Manual installation is possible. It is not recommended and therefore it will not be described here.

# The configuration

## Configure the Integration for the First Time

When adding the Solar Optimizer integration, the common parameters configuration page opens:

![common configuration page](images/config-common-parameters.png)

You need to specify:
1. **A refresh period** in seconds. The shorter the period, the more precise the tracking, but the higher the load on your server, as the calculations are CPU-intensive. A good average value is 5 minutes (i.e., 300 seconds).
2. The sensor that provides **the net instantaneous consumption** of the home (it should be negative if production exceeds consumption). This value is given in Watts.
3. The sensor that provides **the instantaneous photovoltaic production**, also in Watts (it is always positive or zero).
4. A sensor or `input_number` that provides **the cost of imported kWh** (required: strictly positive number).
5. A sensor or `input_number` that provides **the price of exported kWh** (required: strictly positive number). If there is no resale contract, the same value/sensor as the imported cost can be used. Do not set it to 0, as it would distort the algorithm.
6. A sensor or `input_number` that provides **the applicable tax rate on exported kWh** as a percentage (positive number or 0 if you do not resell or do not know this value). This value depends on your contract. It is not critical to the algorithm, so a value of 0 is perfectly fine.
7. An optional sensor that provides **the charge level of a possible solar battery** in percentage. If your solar installation does not include a battery, leave this field empty.
8. A sensor that provides **the net instantaneous charging power of the battery**. It must be expressed in watt and should be negative when the battery is charging and positive when the battery is discharging. This value will be added to the net consumed power. If the net consumed power is -1000 W (selling 1000 W) but the battery is charging at -500 W, it means that the surplus available for the algorithm is 1500 W.
9. **The start time of the day**. At this time, the usage counters of the equipment are reset to zero. The default value is 05:00. Ideally, this should be set before the first production of the day and as late as possible for off-peak activations.

Except for the solar battery charge level, these parameters are essential for the algorithm to function, so they are all mandatory. Using sensors or `input_number` allows values to be updated in real-time at each cycle. Consequently, when off-peak hours begin, the calculation may change, impacting the state of the equipment as importing energy becomes cheaper. Everything is dynamic and recalculated in each cycle.

## Configure the Devices
Each controllable device must be configured by adding a new integration via the "Add a device" button available on the integration page:

![common configuration page](images/config-add-device.png)

The following menu will appear, allowing you to choose between a simple on/off device or a device with variable power (to match the available power):

![device type](images/config-device-type.png)

### Configuring a Simple Device (On/Off)
A simple device is controlled solely by turning it on or off (a switch). If the algorithm decides to turn it on, the device is switched on; otherwise, it is switched off. It is configured as follows:

![simple device configuration](images/config-simple-device.png)

You need to specify the following attributes:

| Attribute                 | Applicable to                       | Meaning                                                                                                                                                                                                                                | Example                                          | Comment                                                                                                                                                                                                           |
| ------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                    | All                                 | The name of the device.                                                                                                                                                                                                                | Basement Ventilation                             | The name is used to identify the entities of this device.                                                                                                                                                         |
| `entity_id`               | All                                 | The entity ID of the device to be controlled.                                                                                                                                                                                          | switch.basement_ventilation                      | Can be a `switch`, an `humidifier`, a `climate`, a `fan`, a `select` or a `light`. If it is not a `switch`, the `activation_service` and `deactivation_service` fields must be adjusted.                          |
| `power_max`               | All                                 | The maximum power consumption of the device when turned on, in watts.                                                                                                                                                                  | 250                                              | -                                                                                                                                                                                                                 |
| `check_usable_template`   | All                                 | A template that evaluates to `True` if the device can be used by Solar Optimizer. A template must start with `{{` and end with `}}`.                                                                                                   | {{ is_state('cover.garage_door', 'closed') }}    | In this example, Solar Optimizer will not attempt to control the "Basement Ventilation" if the garage door is open. Use `{{ True }}` if you do not need this condition.                                           |
| `active_template`         | All                                 | A template that evaluates to `True` if the device is currently active. A template must start with `{{` and end with `}}`. This template is not necessary when the state of the device is 'on' or 'off' when turned-on or off.          | {{ is_state('climate.living_room_ac', 'cool') }} | In this example, a `climate` device will be considered active by Solar Optimizer if its state is `cool`. Leave it blank for devices where the default 'on'/'off' state applies (switches and input_booleans).     |
| `duration_min`            | All                                 | The minimum activation duration in minutes.                                                                                                                                                                                            | 60                                               | The basement ventilation will always run for at least one hour when turned on.                                                                                                                                    |
| `duration_stop_min`       | All                                 | The minimum deactivation duration in minutes. Defaults to `duration_min` if not specified.                                                                                                                                             | 15                                               | The basement ventilation will always remain off for at least 15 minutes before restarting.                                                                                                                        |
| `action_mode`             | All                                 | The action mode used to turn the device on or off. Can be either `"action_call"` or `"event"` (*).                                                                                                                                     | action_call                                      | `"action_call"` indicates that the device is controlled via an action call. See below. `"event"` means an event is triggered when the state should change. See (*) for more details.                              |
| `activation_service`      | Only if `action_mode="action_call"` | The service to call for activating the device, in the format `"domain/service[/parameter:value]"`. This template should be adapted when the device is not a switch.                                                                    | switch/turn_on                                   | Activating the device will trigger the `"switch/turn_on"` service on the `entity_id` specified.                                                                                                                   |
| `deactivation_service`    | Only if `action_mode="action_call"` | The service to call for deactivating the device, in the format `"domain/service[/parameter:value]"`.  This template should be adapted when the device is not a switch.                                                                 | switch/turn_off                                  | Deactivating the device will trigger the `"switch/turn_off"` service on the `entity_id` specified.                                                                                                                |
| `battery_soc_threshold`   | All                                 | The minimum battery charge percentage required for the device to be usable.                                                                                                                                                            | 30                                               | In this example, the device will not be used by the algorithm if the solar battery is not charged to at least 30%. Requires the battery charge state entity to be configured in the common parameters. See above. |
| `max_on_time_per_day_min` | All                                 | The maximum number of minutes the device can be on per day. Once exceeded, the device will no longer be used by the algorithm.                                                                                                         | 10                                               | The device will be turned on for a maximum of 10 minutes per day.                                                                                                                                                 |
| `min_on_time_per_day_min` | All                                 | The minimum number of minutes the device should be on per day. If this threshold is not reached by the start of off-peak hours, the device will be activated until the start of the day or until `max_on_time_per_day_min` is reached. | 5                                                | The device will run for at least 5 minutes per day, either during solar production or during off-peak hours.                                                                                                      |
| `offpeak_time`            | All                                 | The start time of off-peak hours in `hh:mm` format.                                                                                                                                                                                    | 22:00                                            | The device may be turned on at 22:00 if solar production during the day was insufficient.                                                                                                                         |

## Configuring a Device with Variable Power
This type of device allows for adjusting the power consumption based on solar production and the algorithm's decisions. Essentially, it acts as a software-based solar router, enabling, for example, an electric vehicle to charge using only surplus solar energy.

All the parameters described [here](#configuring-a-simple-device-onoff) apply and must be supplemented with the following:

| Attribute                     | Applicable to         | Meaning                                                      | Example                                                  | Comment                                                                                                                                                                                                                                                                                                                                   |
| ----------------------------- | --------------------- | ------------------------------------------------------------ | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `power_entity_id`             | Variable power device | The `entity_id` of the entity managing power levels          | `number.tesla_charging_amps`                             | The power adjustment is done by calling the `change_power_service` on this entity. It can be either a `number`, an `input_number`, a `fan` or a `light`. If it is not a `number`, the `change_power_service` field must be adjusted.                                                                                                      |
| `power_min`                   | Variable power device | The minimum power in watts for the device                    | 100                                                      | If the power setting drops below this value, the device will be turned off via the `deactivation_service`. This parameter works with `power_max` to define the range of power adjustment.                                                                                                                                                 |
| `power_step`                  | Variable power device | The power adjustment step in watts                           | 10                                                       | For an electric vehicle, set this to 220 (220V x 1A).<br/>For `light` entity with `brightness` attribute set it to `power_max / 255`<br/>For `fan` entity with `percentage` attribute set it to `power_max / 100`                                                                                                                         |
| `change_power_service`        | Variable power device | The service to call to adjust power levels                   | `number/set_value`<br/>or<br/>`light/turn_on/brightness` | For `fan` or `light` power entities, you must provide the attribute to set power, typically `brightness` or `percentage`                                                                                                                                                                                                                  |
| `convert_power_divide_factor` | Variable power device | The divisor applied to convert power into the required value | 50                                                       | In this example, the `"number/set_value"` service is called with `power setpoint / 50` on the `entity_id`. For a Tesla in a three-phase installation, the value should be 660 (220V x 3) to convert power into amperes. For a single-phase setup, use 220.<br/>For `light` or `fan` entity set it to the same value of `power_step` field |

## Configuration Examples
The examples below should be adapted to your specific case.

### Controlling Tesla Charging
To control the charging of a Tesla vehicle with adjustable charging intensity, if the solar battery is charged to 50%, in three-phase mode with off-peak charging starting at 11:00 PM, here are the parameters:

```yaml
  name: "Recharge Tesla"
  entity_id: "switch.tesla_charger"
  power_min: 660
  power_max: 3960
  power_step: 660
  check_usable_template: "{{ is_state('input_select.charge_mode', 'Solaire') and is_state('binary_sensor.tesla_wall_connector_vehicle_connected', 'on') and is_state('binary_sensor.tesla_charger', 'on') and states('sensor.tesla_battery') | float(100) < states('number.tesla_charge_limit') | float(90) }}"
  # 2 heures
  duration_min: 120
  # 15 min stop
  duration_stop_min: 15
  # Power management
  power_entity_id: "number.tesla_charging_amps"
  # 5 min
  duration_power_min: 5
  action_mode: "service_call"
  activation_service: "switch/turn_on"
  deactivation_service: "switch/turn_off"
  change_power_service: "number/set_value"
  convert_power_divide_factor: 660
  battery_soc_threshold: 50
  min_on_time_per_day_min: 300
  offpeak_time: "23:00"
```

In single-phase mode, replace 660 with 220. You should at least adjust the maximum power and the `check_usable_template`.

### Controlling an Air Conditioner hvac mode
To turn on an air conditioner if the temperature is above 27°C:

```yaml
    name: "Climatisation salon"
    entity_id: "climate.clim_salon"
    power_max: 1500
    check_usable_template: "{{ states('sensor.temperature_salon') | float(0) > 27 }}"
    active_template: "{{ is_state('climate.vtherm', 'cool') }}"
    # 1 h minimum
    duration_min: 60
    action_mode: "service_call"
    activation_service: "climate/set_hvac_mode/hvac_mode:cool"
    deactivation_service: "climate/set_hvac_mode/hvac_mode:off"
    battery_soc_threshold: 80
```

### Controlling an Air Conditioner preset
To change the preset of an air conditioner if the temperature is above 27°C:

```yaml
    name: "Climatisation salon"
    entity_id: "climate.clim_salon"
    power_max: 1500
    check_usable_template: "{{ states('sensor.temperature_salon') | float(0) > 27 }}"
    active_template: "{{ is_state_attr('climate.clim_salon', 'preset_mode', 'boost') }}"
    # 1 h minimum
    duration_min: 60
    action_mode: "service_call"
    activation_service: "climate/set_preset_mode/preset_mode:boost"
    deactivation_service: "climate/set_preset_mode/preset_mode:eco"
    battery_soc_threshold: 80
```

### Controlling a Dehumidifier
To turn on a dehumidifier if the humidity exceeds a threshold for at least one hour per day, with the possibility of activation during off-peak hours:

```yaml
  name: "Dehumidification musique"
  entity_id: "humidifier.humidifier_musique"
  power_max: 250
  # 1 h
  duration_min: 60
  duration_stop_min: 30
  check_usable_template: "{{ states('sensor.humidite_musique') | float(50) > 55 }}"
  action_mode: "service_call"
  activation_service: "humidifier/turn_on"
  deactivation_service: "humidifier/turn_off"
  max_on_time_per_day_min: 180
  min_on_time_per_day_min: 60
  offpeak_time: "02:00"
```

### Control for a Light

To turn on a light as an indicator of available solar production:

```yaml
  name: "Lighting"
  entity_id: "light.production_indicator_lamp"
  power_max: 100
  check_usable_template: "{{ True }}"
  action_mode: "service_call"
  activation_service: "light/turn_on"
  deactivation_service: "light/turn_off"
  offpeak_time: "02:00"
```

### Control for a dimmable Light

To control light brightness

```yaml
  name: "Eclairage dimmable"
  entity_id: "light.shelly_dimmer"
  power_min: 10
  power_max: 100
  # power_max / 255
  power_step: 0.4
  check_usable_template: "{{ True }}"
  power_entity_id: "light.shelly_dimmer"
  # 5 min
  duration_power_min: 5
  action_mode: "service_call"
  activation_service: "light/turn_on/brightness:0"
  deactivation_service: "light/turn_off"
  change_power_service: "light/turn_on/brightness"
  # same value of power_step
  convert_power_divide_factor: 0.4
  offpeak_time: "02:00"
```

## Configuring the Algorithm in Advanced Mode
Advanced configuration allows modifying the algorithm's settings. It is not recommended to change these settings unless you have specific needs. The algorithm uses a **simulated annealing** approach to search for optimal configurations (combinations of on/off states) and evaluates a cost function at each iteration.

During each iteration, the algorithm randomly changes the state of some devices and evaluates the cost function. If the new evaluation is better than the previous one, it is kept. If it is worse, it may still be kept based on a "temperature" parameter. This temperature gradually decreases over iterations, allowing the algorithm to converge toward an optimal solution.

### Enabling Advanced Configuration
To use the advanced configuration, follow these steps:

1. Add the following line to your `configuration.yaml` file:

   ```yaml
   solar_optimizer: !include solar_optimizer.yaml
   ```
2.	Create a file named solar_optimizer.yaml at the same level as configuration.yaml and include the following settings:

  ``` yaml
  algorithm:
    initial_temp: 1000
    min_temp: 0.1
    cooling_factor: 0.95
    max_iteration_number: 1000
  ```

Explanation of Parameters
	•	`initial_temp`: The initial temperature. Cost function variations up to 1000 are accepted in the first iterations. If you have high-power devices, you may increase this value. For lower-power devices, it can be reduced.
	•	`min_temp`: The minimum temperature. At the final stage of the optimization, only variations of 0.1 will be accepted. This parameter should not be modified.
	•	`cooling_factor`: The temperature is multiplied by 0.95 at each iteration, ensuring a slow and progressive decrease. A lower value makes the algorithm converge faster but may reduce solution quality.	A higher value (strictly less than 1) increases computation time but improves the solution quality.
	•	`max_iteration_number`: The maximum number of iterations. Reducing this number can shorten computation time but may degrade solution quality if no stable solution is found.

The default values are suited for setups with around 20 devices (which results in many possible configurations). If you have fewer than 5 devices and no variable power devices, you can try these alternative parameters (not tested):

  ```yaml
  algorithm:
    initial_temp: 1000
    min_temp: 0.1
    cooling_factor: 0.90
    max_iteration_number: 300
  ```

# Available Entities
## The "configuration" Device
Once the integration is properly configured, a **device** named `'configuration'` is created, containing several entities:

1. A sensor named `total_power`: the total power of all devices controlled by Solar Optimizer.
2. A sensor named `best_objective`: the cost function value (see algorithm operation). The **lower** the value, the **better** the solution.
3. A sensor named `power_production`: the last **smoothed** solar production value considered (if the option is enabled).
4. A sensor named `power_production_brut`: the last **raw** solar production value considered.
5. a dropdown list named `priority weight` which defines the weight given to priority management compared to solar consumption optimization. See [priority management](#priority-management).

![Configuration Entities](images/entities-configuration.png)

Reconfiguring this device allows modifying the **Solar Optimizer** settings.

## Devices and Their Entities
Each controlled device has the following entities:

1. A **switch** named `switch.enable_solar_optimizer_<name>`:
   - If **"Off"**, the device is ignored by the algorithm.
   - This allows manually **excluding** a device **without modifying** the configuration.
   - This switch contains **additional attributes** to monitor the device's internal state as seen by the algorithm.

2. A **sensor** named `sensor.on_time_today_solar_optimizer_<name>`:
   - Indicates the **activation duration** since the last reset (**see `raz_time`**).

3. A **switch** named `switch.solar_optimizer_<name>`:
   - Reflects the **activation state** requested by **Solar Optimizer**.

4. A dropdown list named **"Priority"** which defines the priority level of this device. Possible values range from 'Very low' to 'Very high'. See [priority management](#priority-management).

![Simple Device Entities](images/entities-simple-device.png)

### Switch Attributes
The `switch.solar_optimizer_<name>` contains **attributes** accessible via **Developer Tools → States**:

![Configuration Entities](images/entities-attributes.png)

| Attribute Name              | Description                                                                                 |
| --------------------------- | ------------------------------------------------------------------------------------------- |
| `is_enabled`                | `true` if the device is enabled by the user for optimization.                               |
| `is_active`                 | `true` if the device is currently **on**.                                                   |
| `is_usable`                 | `true` if the algorithm **can** use the device.                                             |
| `can_change_power`          | `true` if the device's power **can** be adjusted.                                           |
| `current_power`             | The **current power consumption** of the device.                                            |
| `requested_power`           | The power level requested by **Solar Optimizer**.                                           |
| `duration_sec`              | The total **activation duration** in seconds.                                               |
| `duration_power_sec`        | The duration of the **last power change** in seconds.                                       |
| `next_date_available`       | The **next available time** for the device to be used by the algorithm.                     |
| `next_date_available_power` | The **next available time** for a power adjustment.                                         |
| `battery_soc_threshold`     | The **minimum** battery **state of charge (SOC)** required for the device to be considered. |
| `battery_soc`               | The **current** battery **state of charge (SOC)**.                                          |

# Priority Management

From the user’s perspective, two values must be provided:

1. **Priority weight** — this is the weight given to priority compared to solar consumption optimization. These two notions are somewhat contradictory: optimizing solar production usage can conflict with prioritizing specific devices. A prioritized device may be turned on more often, potentially reducing optimization efficiency. This setting is available in the "Configuration" device as a `select` entity.

2. **Device priority** — this defines the priority level for each individual device. It is a selectable list with five values ranging from 'Very low' to 'Very high'. The higher the priority, the more likely the device is to be activated by the algorithm. This setting is available in the device entity as a `select`.

## Priority Weight

![priority weight](images/entity-priority-weight.png)

The higher this value is, the more priority is considered by the algorithm at the expense of optimization. Selecting `None` fully disables the priority mechanism and ensures maximum optimization of solar consumption.

## Device Priority

![priority](images/entities-priority.png)

The higher the priority, the more often the device will be activated by the algorithm, potentially at the expense of lower-priority devices.

> ![Note](images/tips.png) _*Notes*_
> 1. Prioritizing certain devices can reduce solar production consumption efficiency. It is normal to observe unused surplus if priorities are enabled. You can adjust how much priority impacts the algorithm by changing the [priority weight](#priority-weight).
> 2. Priority is not absolute — it is possible for a lower-priority device to be turned on while a higher-priority one is not. This depends on factors like device power usage, available solar power, minimum run times, etc. If this happens too often, fine-tune the priority level or the priority weight as explained above.

# Events

Solar Optimizer generates events each time a device is turned on or off. This allows you to capture these events in an automation, for example.

`solar_optimizer_state_change_event`: Triggered when a device changes state. The event message contains the following data:
```
event_type: solar_optimizer_state_change_event
data:
  action_type: [Activate | Deactivate],
  requested_power: <la nouvelle puissance demandée si disponible>,
  current_power: <la puissance demandée si disponible>,
  entity_id: <l'entity_id de l'appareil commandé>,
```

`solar_optimizer_change_power_event`: Triggered when a device changes power. The event message contains the following data:
```
event_type: solar_optimizer_state_change_event
data:
  action_type: [ChangePower],
  requested_power: <la nouvelle puissance demandée si disponible>,
  current_power: <la puissance demandée si disponible>,
  entity_id: <l'entity_id de l'appareil commandé>,
```

You can monitor the reception and content of events in Developer Tools / Events. Enter the name of the event to listen for:

![Event Listening](images/event-listening.png)

An example of an automation that listens for events:

```yaml
alias: Gestion des events de Solar Optimizer
description: Notifie les modifiations de status de Solar Optimizer
mode: parallel
max: 50
triggers:
  - event_type: solar_optimizer_change_power_event
    id: power_event
    trigger: event
  - event_type: solar_optimizer_state_change_event
    id: state_change
    trigger: event
conditions: []
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: power_event
        sequence:
          - data:
              message: >-
                {{ trigger.event.data.action_type }} pour entité {{
                trigger.event.data.entity_id}}     avec requested_power {{
                trigger.event.data.requested_power }}. (current_power is {{
                trigger.event.data.current_power }})
              title: ChangePower Event de Solar Optimizer
            enabled: false
            action: persistent_notification.create
          - if:
              - condition: template
                value_template: >-
                  {{ trigger.event.data.entity_id == switch.cloucloute_charger
                  }}
            then:
              - data:
                  message: On demande a changer la puissance de Cloucloute
                  title: Changement de puissance
                  notification_id: cloucloute-power-change
                action: persistent_notification.create
              - data:
                  value: >-
                    {{ (trigger.event.data.requested_power | float(0) / 660) |
                    round(0) }}
                target:
                  entity_id: number.cloucloute_charging_amps
                action: number.set_value
      - conditions:
          - condition: trigger
            id: state_change
        sequence:
          - data:
              message: >-
                {{ trigger.event.data.action_type }} pour entité {{
                trigger.event.data.entity_id}}     avec requested_power {{
                trigger.event.data.requested_power }}. (current_power is {{
                trigger.event.data.current_power }})
              title: StateChange Event de Solar Optimizer
            action: persistent_notification.create
```
# Actions

Solar Optimizer provides actions that allow you to interact with SO. These actions can be used through Developer Tools / Actions as well as in automations.

## reset_on_time

This action resets the activation time of a device.

To use it, go to Developer Tools / Actions, type "Solar Optimizer" and you will see the `reset_on_time` action.
Select it, choose the relevant device(s) to apply the action to, and click **"Run Action"**.

You should see something like this:

![action reset_on_time](images/run-action-reset-on-time.png)

In YAML mode, it should look like this:

```yaml
action: solar_optimizer.reset_on_time
target:
  device_id: 825afe5fcee088d82d024f5f925cdb3e
data: {}
```

# Creating Sensor Templates for Your Installation

Your setup may require the creation of specific sensors that need to be configured [here](README-en.md#configure-the-integration-for-the-first-time). The rules for these sensors are crucial and must be strictly followed to ensure the proper functioning of Solar Optimizer.

Below are my sensor templates (applicable only for an Enphase installation):

### File `configuration.yaml`:
```
template: !include templates.yaml
```

### File `templates.yaml`:
```
- sensor:
    - name: "Total power instanteneous production (W)"
      icon: mdi:solar-power-variant
      unique_id: total_power_produite_w
      device_class: power
      unit_of_measurement: "W"
      state_class: measurement
      state: >
        {% set power = [states('sensor.envoy_xxxxx_current_power_production') | float(default=0), 0] | max %}
        {{ power | round(2) }}
      availability: "{{ is_number(states('sensor.envoy_xxxxx_current_power_production')) }}"
    - name: "Total power consumption net instantaneous (W)"
      unique_id: total_power_consommee_net_w
      unit_of_measurement: "W"
      device_class: power
      state_class: measurement
      state: >
        {%- set power_net = states('sensor.envoy_xxxxx_current_net_power_consumption') | float(default=0) -%}
        {{ power_net }}
      availability: "{{ is_number(states('sensor.envoy_xxxxx_current_net_power_consumption')) }}"
```

Adapt these to fit your specific setup.

# A Card for Your Dashboards as a complement
As a complement, the following Lovelace code allows you to control each declared device.
The steps to follow are:
1. Using HACS, install the plugins named `streamline-card`, `expander-card`, and `mushroom-template` if you haven't already.
2. Install the templates for `streamline` at the top of your Lovelace code.
3. Add one card per device managed by Solar Optimizer, referencing the `streamline` template.

## Install the Plugins
Read the plugin documentation [here](https://github.com/brunosabot/streamline-card) to familiarize yourself with this excellent plugin.
Follow the installation procedure, which consists of adding a new GitHub repository of type `Dashboard` and installing the plugin.

In the "Downloaded" section, you should see your installed plugins:

![HACS Plugin](images/install-hacs-streamline.png)

Do the same for the `expander-card` and `mushroom-template` plugins.

## Install the Templates
To install the templates, go to your dashboard, enter edit mode, and click on the three dots in the menu at the top right:

![dashboard edit](images/dashboard-edit.png)

Then:

![dashboard edit 2](images/dashboard-edit2.png)

And then:

![dashboard edit 3](images/dashboard-edit3.png)

You will now be in the manual edit mode of your Lovelace dashboard.

**Warning:** YAML is sensitive to formatting. Indentation must be strictly respected.

Copy and paste the text below (click the copy button to grab everything safely) at the very beginning, one line, one column.

```yaml
# To be put on the top of your dashboard code
streamline_templates:
  managed_device_power:
    default: null
    card:
      type: custom:expander-card
      expanded: false
      title-card-button-overlay: true
      title-card:
        type: custom:mushroom-template-card
        primary: '{{ state_attr(''[[device]]'', ''device_name'') }}'
        secondary: >-
          [[secondary_infos]] ({{ state_attr('[[on_time_entity]]',
          'on_time_hms') }} / {{ state_attr('[[on_time_entity]]',
          'max_on_time_hms')}} )
        icon: '[[icon]]'
        badge_icon: >-
          {% if is_state_attr('[[on_time_entity]]','should_be_forced_offpeak',
          True) %}mdi:power-sleep{% elif
          is_state_attr('[[device]]','is_enabled', True) %}mdi:check{% else
          %}mdi:cancel{% endif %}
        badge_color: >-
          {% if is_state_attr('[[on_time_entity]]','should_be_forced_offpeak',
          True) %}#003366{% elif is_state_attr('[[device]]', 'is_usable', True)
          and is_state_attr('[[device]]', 'is_enabled', True) %}green {% elif
          is_state_attr('[[device]]', 'is_enabled', False) %}red {% elif
          is_state_attr('[[device]]','is_waiting', True) %}orange {% elif
          is_state_attr('[[device]]', 'is_usable', False) or
          state_attr('[[device]]', 'is_usable') is none %}#A0B0FF{% else
          %}blue{% endif %}
        entity: '[[device]]'
        icon_color: >-
          {% if is_state('[[device]]', 'on')%}orange{% else %}lightgray{% endif
          %}
        tap_action:
          action: toggle
        hold_action:
          action: more-info
        double_tap_action:
          action: none
      cards:
        - type: custom:mushroom-chips-card
          chips:
            - type: entity
              entity: '[[enable_entity]]'
              double_tap_action:
                action: more-info
              tap_action:
                action: toggle
              hold_action:
                action: more-info
              icon_color: green
              content_info: name
        - type: markdown
          content: >-
            **Prochaine dispo** : {{ ((as_timestamp(state_attr('[[device]]',
            'next_date_available')) - as_timestamp(now())) / 60) | int }}
            min<br> **Prochaine dispo puissance**: {{
            ((as_timestamp(state_attr('[[device]]',
            'next_date_available_power')) - as_timestamp(now())) / 60) | int }}
            min<br> **Utilisable** : {{ state_attr('[[device]]', 'is_usable')
            }}<br> **Est en attente**  : {{ state_attr('[[device]]',
            'is_waiting') }}<br> **Est forcé en heures creuses**  : {{
            state_attr('[[on_time_entity]]', 'should_be_forced_offpeak') }}<br>
            **Heures creuses**  : {{ state_attr('[[on_time_entity]]',
            'offpeak_time') }}<br> **Puissance requise** : {{
            state_attr('[[device]]', 'requested_power') }} W<br> **Puissance
            courante** : {{ state_attr('[[device]]', 'current_power') }} W
          title: Infos
        - type: history-graph
          hours: 24
          entities:
            - entity: '[[device]]'
            - entity: '[[enable_entity]]'
            - entity: '[[power_entity]]'
  managed_device:
    default: null
    card:
      type: custom:expander-card
      expanded: false
      title-card-button-overlay: true
      title-card:
        type: custom:mushroom-template-card
        primary: '{{ state_attr(''[[device]]'', ''device_name'') }}'
        secondary: >-
          [[secondary_infos]] (max. {{ state_attr('[[device]]', 'power_max') }}
          W -  {{ state_attr('[[on_time_entity]]', 'on_time_hms')}} / {{
          state_attr('[[on_time_entity]]', 'max_on_time_hms')}} )
        icon: '[[icon]]'
        badge_icon: >-
          {% if is_state_attr('[[on_time_entity]]','should_be_forced_offpeak',
          True) %}mdi:power-sleep{% elif
          is_state_attr('[[device]]','is_enabled', True) %}mdi:check{% else
          %}mdi:cancel{% endif %}
        badge_color: >-
          {% if is_state_attr('[[on_time_entity]]','should_be_forced_offpeak',
          True) %}#003366{% elif is_state_attr('[[device]]', 'is_usable', True)
          and is_state_attr('[[device]]', 'is_enabled', True) %}green {% elif
          is_state_attr('[[device]]', 'is_enabled', False) %}red {% elif
          is_state_attr('[[device]]','is_waiting', True) %}orange {% elif
          is_state_attr('[[device]]', 'is_usable', False) or
          state_attr('[[device]]', 'is_usable') is none %}#A0B0FF{% else
          %}blue{% endif %}
        entity: '[[device]]'
        icon_color: >-
          {% if is_state('[[device]]', 'on')%}orange{% else %}lightgray{% endif
          %}
        tap_action:
          action: toggle
        hold_action:
          action: more-info
        double_tap_action:
          action: none
      cards:
        - type: custom:mushroom-chips-card
          chips:
            - type: entity
              entity: '[[enable_entity]]'
              double_tap_action:
                action: more-info
              tap_action:
                action: toggle
              hold_action:
                action: more-info
              icon_color: green
              content_info: name
        - type: markdown
          content: >-
            **Prochaine dispo** : {{ ((as_timestamp(state_attr('[[device]]',
            'next_date_available')) - as_timestamp(now())) / 60) | int }}
            min<br> **Utilisable** : {{ state_attr('[[device]]', 'is_usable')
            }}<br> **Est en attente**  : {{ state_attr('[[device]]',
            'is_waiting') }}<br> **Est forcé en heures creuses**  : {{
            state_attr('[[on_time_entity]]', 'should_be_forced_offpeak') }}<br>
            **Heures creuses**  : {{ state_attr('[[on_time_entity]]',
            'offpeak_time') }}<br> **Puissance requise** : {{
            state_attr('[[device]]', 'requested_power') }} W<br> **Puissance
            courante** : {{ state_attr('[[device]]', 'current_power') }} W
        - type: history-graph
          hours: 24
          entities:
            - entity: '[[device]]'
            - entity: '[[enable_entity]]'
            - entity: '[[power_entity]]'
```

You should now see a page that looks like this:

![dashboard edit 4](images/dashboard-edit4.png)

Click "Save" and then "Finish." The templates are now installed; all that's left is to use them.

## Add a Card for Each Device

To use the templates installed in the previous step, follow these instructions:
1. Edit a dashboard where you want to add the card.
2. Click "Add a card" at the bottom right.
3. Select the card named **Streamline Card** as shown below:

![dashboard edit 4](images/add-card-1.png)

4. Fill in the fields as follows:

![dashboard edit 4](images/add-card-2.png)

You should choose the `managed_device` template for a device without power modulation or `managed_device_power` otherwise.
Then, enter the different attributes.

A complete example for a **non-power** device:

![dashboard edit 4](images/add-card-3.png)

And for a **power-modulated** device:

![dashboard edit 4](images/add-card-4.png)

You will then get a component that allows you to interact with the device, which looks like this:

![Lovelace devices](https://github.com/jmcollin78/solar_optimizer/blob/main/images/lovelace-eqts.png?raw=true)

## Using the Card

The card allows you to monitor the device’s usage status and interact with it. Open the card by pressing the "V," and you will see this:

![use card 1](images/use-card-1.png)

### Icon Color

| Color  | Meaning    | Example                              |
| ------ | ---------- | ------------------------------------ |
| Gray   | Device off | ![use card 2](images/use-card-2.png) |
| Yellow | Device on  | ![use card 3](images/use-card-3.png) |

### Badge

| Icon / Color | Meaning                                                | Example                                         |
| ------------ | ------------------------------------------------------ | ----------------------------------------------- |
| Green check  | Device off, waiting for power production               | ![use card 4](images/use-card-green-check.png)  |
| Blue check   | Device off, unavailable (`check-usable` returns false) | ![use card 4](images/use-card-blue-check.png)   |
| Orange check | Device off, waiting for delay between two activations  | ![use card 4](images/use-card-orange-check.png) |
| Red cancel   | Device off, not allowed (`enable` is false)            | ![use card 4](images/use-card-red-cancel.png)   |
| Blue moon    | Device on during off-peak hours                        | ![use card 4](images/use-card-blue-moon.png)    |

### Actions on the Card

- Click on the device card to force it **on or off**.
- Click on the `Enable` button to allow or prevent the **Solar Optimizer algorithm** from using the device.

# Contributions are welcome!

If you would like to contribute, please read the [contribution guidelines](CONTRIBUTING.md)

***

[solar_optimizer]: https://github.com/jmcollin78/solar_optimizer
[buymecoffee]: https://www.buymeacoffee.com/jmcollin78
[buymecoffeebadge]: https://img.shields.io/badge/Buy%20me%20a%20beer-%245-orange?style=for-the-badge&logo=buy-me-a-beer
[commits-shield]: https://img.shields.io/github/commit-activity/y/jmcollin78/solar_optimizer.svg?style=for-the-badge
[commits]: https://github.com/jmcollin78/solar_optimizer/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://forum.hacf.fr/
[license-shield]: https://img.shields.io/github/license/jmcollin78/solar_optimizer.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Joakim%20Sørensen%20%40ludeeus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jmcollin78/solar_optimizer.svg?style=for-the-badge
[releases]: https://github.com/jmcollin78/solar_optimizer/releases
