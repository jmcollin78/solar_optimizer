"""Describe the Solar Optimizer events in the logbook. The solar_optimizer_action event is
fired first with the Context of each action, so the change of the device is shown as
triggered by Solar Optimizer."""

from collections.abc import Callable

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_ICON,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN, EVENT_TYPE_SOLAR_OPTIMIZER_ACTION

# Keys are the action types of managed_device.py (Activate, Deactivate, ChangePower)
MESSAGES = {
    "en": {"Activate": "turned on {device}", "Deactivate": "turned off {device}", "ChangePower": "set {device} to {power} W"},
    "fr": {"Activate": "a allumé {device}", "Deactivate": "a éteint {device}", "ChangePower": "a réglé {device} à {power} W"},
    "it": {"Activate": "ha acceso {device}", "Deactivate": "ha spento {device}", "ChangePower": "ha impostato {device} a {power} W"},
    "es": {"Activate": "encendió {device}", "Deactivate": "apagó {device}", "ChangePower": "ajustó {device} a {power} W"},
}


def describe_action(language: str, data: dict) -> str:
    """The message of a solar_optimizer_action event, with the configured service of the
    device ("climate/set_hvac_mode/hvac_mode:cool" is shown as "climate.set_hvac_mode hvac_mode:cool")"""
    messages = MESSAGES.get((language or "en")[:2], MESSAGES["en"])
    template = messages.get(data.get("action"), "{device}")
    message = template.format(device=data.get("device_name"), power=data.get("requested_power"))
    if service := data.get("service"):
        domain, _, rest = service.partition("/")
        service_name, _, parameter = rest.partition("/")
        message += f" ({domain}.{service_name}{' ' + parameter if parameter else ''})"
    return message


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe the Solar Optimizer logbook events"""

    @callback
    def async_describe_action(event: Event) -> dict[str, str]:
        return {
            LOGBOOK_ENTRY_NAME: "Solar Optimizer",
            LOGBOOK_ENTRY_MESSAGE: describe_action(hass.config.language, event.data),
            LOGBOOK_ENTRY_ENTITY_ID: event.data.get("entity_id"),
            LOGBOOK_ENTRY_ICON: "mdi:solar-power-variant",
        }

    async_describe_event(DOMAIN, EVENT_TYPE_SOLAR_OPTIMIZER_ACTION, async_describe_action)
