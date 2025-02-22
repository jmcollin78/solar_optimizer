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
- [How do we install it?](#how-do-we-install-it)
  - [HACS installation (recommended)](#hacs-installation-recommended)
  - [Manual Install](#manual-install)
- [The configuration](#the-configuration)
  - [Configure integration](#configure-integration)
  - [Configure equipment](#configure-equipment)
- [Available entities](#available-entities)
- [In addition](#in-addition)
- [Contributions are welcome!](#contributions-are-welcome)


>![New](https://github.com/jmcollin78/solar_optimizer/blob/main/images/new-icon.png?raw=true) _*News*_
> * **release 2.1.0** :
> - added a minimum duration of ignition during off-peak hours. Allows you to manage equipment that must have a minimum of ignition per day such as water heaters or chargers (cars, battery, ...). If the sunshine has not reached the required duration, then the equipment will turn on during off-peak hours. You can also define at what time the ignition counters are reset to zero, which allows you to take advantage of all off-peak hours> * **release 2.0.0** :
> - added a device per controlled equipment to group the entities,
> - added an ignition time counter for each device. When the controlled switch goes to 'Off', the time counter is incremented by the time spent 'On', in seconds. This counter is reset to zero every day at midnight.
> - added a maximum time to 'On' in the configuration (in minutes). When this duration is exceeded, the equipment is no longer usable by the algorithm (is_usable = off) until the next reset. This offers the possibility of not exceeding a maximum ignition time per day, even when solar power is available.
> - to take advantage of this new information, don't forget to update the decluterring template (at the end of this file)
> - this release opens the door to more significant developments based on the ignition time (having a daily minimum for example) and prepares the ground for the arrival of the configuration via the graphical interface.
* **release 1.7.0**:
- added battery management. You can specify a percentage type entity that gives the state of charge of the battery (soc). On each device you can specify a `battery_soc_threshold` parameter: the battery threshold below which the device will not be usable.
* **release 1.3.0**:
  - added the parameter `duration_stop_min` which allows to specify a minimal duration of deactivation to distinguish it from the minimal delay of activation `duration_min`. If not specified, this parameter takes the value of `duration_min`.
  - restores the state of the `enable` switches when the integration starts.
  - starts a calculation immediately after starting Home Assistant
* **release 1.0**: first operational version. Control of equipment based on switches, power control (Tesla) and configuration via configuration.yaml.

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
Each configured device is associated with a switch-type entity that authorizes the algorithm to use the device. If I want to force the heating of the hot water tank, I put its switch to off. The algorithm will therefore not look at it, the water heater switches back to manual, not managed by Solar Optimizer.

In addition, it is possible to define a usability rule for equipment. For example, if the car is charged at more than 90%, the algorithm considers that the equipment which controls the charging of the car must be switched off. This rule is defined in the form of a configurable template which is True if the equipment is usable.

If a battery is specified when configuring the integration and if the threshold `battery_soc_threshold` is specified, the equipment will only be usable if the soc (percentage of battery charge) is greater than or equal to the threshold.

A maximum daily usage time is optionally configurable. If it is valued and if the duration of use of the equipment is exceeded, then the equipment will not be usable by the algorithm and therefore leaves power for other equipment.

A minimum daily usage time is also optionally configurable. This parameter ensures that the equipment will be on for a certain minimum duration. You specify at what time the off-peak hours start (`offpeak_time`) and the minimum duration in minutes (`min_on_time_per_day_min`). If at the time indicated by `offpeak_time`, the minimum activation duration has not been reached, then the equipment is activated until the change of day (configurable in the integration and 05:00 by default) or until the maximum usage is reached (`max_on_time_per_day_min`) or during all the off-peak hours if `max_on_time_per_day_min` is not set. This ensures that the water heater or the car will be charged the next morning even if the solar production has not allowed the device to be recharged. It is up to you to invent the uses of this function.

These 5 rules allow the algorithm to only order what is really useful at a time t. These rules are re-evaluated at each cycle.

# How do we install it?
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
## Configure integration
When adding the Solar Optimizer integration, the following settings page opens:

You must specify:
1. the sensor which gives the instantaneous net consumption of the dwelling (it must be negative if production exceeds consumption). This figure is indicated in Watt,
2. the sensor which gives the instantaneous photovoltaic production in Watt too,
3. a sensor or input_number which gives the cost of the imported kwh (require: positive number, not zero),
4. a sensor or input_number which gives the price of the exported kwh (require: positive number, not zero)(depends on your contract), can re-use same sensor/input_number as imported kwh if no have a resale contract.
5. a sensor or input_number which gives the applicable tax on the exported kwh (require: postive number or zero)(depends on your contract)
6. the start time of the day. At this time the equipment usage counters are reset to zero. The default value is 05:00. It must be before the first production and as late as possible for activations during off-peak hours. See above.

These 5 pieces of information are necessary for the algorithm to work, so they are all mandatory. The fact that they are sensors or input_number allows to have values that are re-evaluated at each cycle. Consequently, switching to off-peak hours can modify the calculation and therefore the states of the equipment since the import becomes less expensive. So everything is dynamic and recalculated at each cycle.

## Configure equipment
Controllable devices are defined in the configuration.yaml file as follows:
- add the following line in your configuration.yaml:

   ```solar_optimizer: !include solar_optimizer.yaml```
- and create a file at the same level as the configuration.yaml with the following information:
```
algorithm:
   initial_temp: 1000
   min_temp: 0.1
   cooling_factor: 0.95
   max_iteration_number: 1000
devices:
   - name: "<equipment name>"
     entity_id: "switch.xxxxx"
     power_max: <max power consumed>
     check_usable_template: "{{ <the template which is True if the equipment is usable> }}"
     duration_min: <the minimum activation duration in minutes>
     duration_stop_min: <minimum stop duration in minutes>
     action_mode: "service_call"
     activation_service: "<service name>"
     deactivation_service: "<service name>"
     battery_soc_threshold: <the state of charge minimal to use this device>
     max_on_time_per_day_min: <the maximum time on 'on' per day in minutes>
     offpeak_time: <start time of off-peak hours>
     min_on_time_per_day_min: <the minimal time on 'on' per day in minutes>
```

Note: parameters under `algorithm` should not be touched unless you know exactly what you are doing.

Under `devices` you must declare all the equipment that will be controlled by Solar Optimizer as follows:

| attribute | valid for | meaning | example | comment |
| ----------------------- | ---------------------------------------- | -------------------------------------------- | ------------------------------------------------------- | ------------------------------------ |
| `name` | all | The name of the equipment | "VMC basement" | - |
| `entity_id` | all | the entity id of the equipment to order | "switch.vmc_basement" | - |
| `power_max` | all | the maximum power consumed by the equipment | 250 | - |
| `check_usable_template` | all | A template that is True if the equipment can be used by Solar Optimizer | "{{ is_state('cover.porte_garage_garage', 'closed') }}" | In the example, Sonar Optimizer will not try to control the "VMC basement" if the garage door is open |
| `duration_min` | all | The minimum duration in minutes of activation | 60 | The basement VMC will always turn on for at least one hour |
| `duration_stop_min` | all | The minimum duration in minutes of deactivation. Is `duration_min` if not specified | 15 | The basement VMC will always turn off for at least 15 min |
| `action_mode` | all | the mode of action for turning the equipment on or off. Can be "service_call" or "event" (*) | "service_call" | "service_call" indicates that the equipment is switched on and off via a service call. See below. "event" indicates that an event is sent when the state should change. See (*) |
| `activation_service` | only if action_mode="service_call" | the service to be called to activate the equipment in the form "domain/service" | "switch/turn_on" | activation will trigger the "switch/turn_on" service on the entity "entity_id" |
| `deactivation_service` | only if action_mode="service_call" | the service to call to deactivate the equipment in the form "domain/service" | "switch/turn_off" | deactivation will trigger the "switch/turn_off" service on the entity "entity_id" |
| `battery_soc_threshold`  | tous | minimal percentage of charge of the solar battery to enable this device            | 30                                       |                                                                                                     |
| `max_on_time_per_day_min` | all | the maximum number of minutes in the on position for this equipment. Beyond that, the equipment is no longer usable by the algorithm | 10 | The equipment will be on for a maximum of 10 minutes per day |
| `offpeak_time` | all | The start time of off-peak hours in hh:mm format | "22:00" | The equipment can be switched on at 22:00 if the production of the day has not been sufficient |
| `min_on_time_per_day_min` | all | the minimum number of minutes in the on position for this equipment. If at the start of off-peak hours, this minimum is not reached then the equipment will be switched on up to the start of the day or the `max_on_time_per_day_min` | 5 | The equipment will be switched on for a minimum of 5 minutes per day |

For variable power equipment, the following attributes must be valued:

| attribute | valid for | meaning | example | comment |
| ----------------------------- | ------------------------------- | ----------------------------------------------------------- | ---------------------------- | ---------------------------------------------------- |
| `power_entity_id` | variable power equipment | the entity_id of the entity managing the power | `number.tesla_charging_amps` | The power change will be done by calling the `change_power_service` service on this entity |
| `power_min` | variable power equipment | The minimum power in watts of the equipment | 100 | When the power setpoint falls below this value, the equipment will be switched off by calling the `deactivation_service` |
| `power_step` | variable power equipment | The power step | 10 | - |
| `change_power_service` | variable power equipment | Service called to change power | `"number/set_value"` | - |
| `convert_power_divide_factor` | variable power equipment | The divisor applied to convert power to value | 50 | In the example, the "number/set_value" service will be called with the `power setpoint / 50` on the entity `entity_id`. For a Tesla on a three-phase electrical installation this parameter should be set to 660 (220 x 3), to convert power to amperes. For mono-phase installation, set it to 220. |

Complete and commented example of the device part:
```
devices:
   - name: "Reservoir pump"
     # The switch that controls the tank pump
     entity_id: "switch.tank_pump_socket"
     # the power of this pump
     power_max: 170
     # Always usable
     # check_usable_template: "{{ True }}"
     # 15 min minimum activation
     duration_min: 15
     # 5 min deactivation minimum
     duration_stop_min: 5
     # On enable/disable via a service call
     action_mode: "service_call"
     # The service enabling the switch
     activation_service: "switch/turn_on"
     # The service to deactivate the switch
     deactivation_service: "switch/turn_off"
     # We authorize the pump to start if there is 10% battery in the solar installation
     battery_soc_threshold: 10
     # One hour per day maximum
     max_on_time_per_day_min: 60
     # 1/2h per day minimum ...
     min_on_time_per_day_min: 30
     # ... starting at 22:30
     offpeak_time: "22:30"

   - name: "Tesla Recharge"
     entity_id: "switch.cloucloute_charger"
     # The minimum load power is 660 W (i.e. 1 Amp because convert_power_divide_factor=660 too)
     power_min: 660
     # The minimum load power is 3960 W (i.e. 5 Amp (= 3960/600) )
     power_max: 3960
     # the step of 660 or 1 Amp after division by convert_power_divide_factor
     power_step: 660
     # Usable if the charging mode is "Solar" and the car is plugged into the charger and it is charged at less than 90% (so it stops by itself at 90%)
     check_usable_template: "{{ is_state('input_select.charge_mode', 'Solar') and is_state('binary_sensor.tesla_wall_connector_vehicle_connected', 'on') and is_state('binary_sensor.tesla_charger', 'on') and states('sensor.tesla_battery ') | float(100) < states('number.cloucloute_charge_limit') | float(90) }}"
     # 1 hour minimum charge
     duration_min: 60
     # 15 min minimum stop charge
     duration_stop_min: 15
     # The entity that drives the load amperage
     power_entity_id: "number.tesla_charging_amps"
     # 5 min minimum between 2 power changes
     duration_power_min: 5
     # activation is done by a service call
     action_mode: "service_call"
     activation_service: "switch/turn_on"
     deactivation_service: "switch/turn_off"
     # the power change is done by a service call
     change_power_service: "number/set_value"
     # the factor used to convert the set power into Amps (number.tesla_charging_amps takes Amps)
     convert_power_divide_factor: 660
     # We do not start a charge if the battery of the solar installation is not at least 50% charged
     battery_soc_threshold: 50
     # 4h par day minimum ...
     min_on_time_per_day_min: 240
     # ... starting at 23:00
     offpeak_time: "22:00"
...
```
Any change in the configuration requires a stop / restart of the integration (or of Home Assistant) to be taken into account.

# Available entities
The integration, once properly configured, creates a device that contains several entities:
1. a sensor named "total_power" which is the total of all the powers of the equipment controlled by Solar Optimizer,
2. a sensor named "best_objective" which is the value of the cost function (see how the algorithm works),
3. a switch per equipment named `switch.enable_solar_optimizer_<name>` declared in the configuration.yaml. If the switch is "Off", the algorithm will not consider this equipment for the calculation. This allows you to manually remove equipment from the list without having to modify the list. This switch contains additional attributes which make it possible to follow the internal state of the equipment seen by the algorithm.

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

| Color | Meaning | Example |
|---------|---------|---------|
| Gray | Device off | ![use card 2](images/use-card-2.png) |
| Yellow | Device on | ![use card 3](images/use-card-3.png) |

### Badge

| Icon / Color | Meaning | Example |
|---------|---------|---------|
| Green check | Device off, waiting for power production | ![use card 4](images/use-card-green-check.png) |
| Blue check | Device off, unavailable (`check-usable` returns false) | ![use card 4](images/use-card-blue-check.png) |
| Orange check | Device off, waiting for delay between two activations | ![use card 4](images/use-card-orange-check.png) |
| Red cancel | Device off, not allowed (`enable` is false) | ![use card 4](images/use-card-red-cancel.png) |
| Blue moon | Device on during off-peak hours | ![use card 4](images/use-card-blue-moon.png) |

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
