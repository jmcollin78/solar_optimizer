"""Unit tests for the timed activation feature (forced activation with duration)"""

# pylint: disable=protected-access

from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN

from custom_components.solar_optimizer.const import get_tz
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


# ---------------------------------------------------------------------------
# Helper: configuration de base d'un device A
# ---------------------------------------------------------------------------

DEVICE_A_DATA = {
    CONF_NAME: "Equipement A",
    CONF_DEVICE_TYPE: CONF_DEVICE,
    CONF_ENTITY_ID: "input_boolean.fake_device_a",
    CONF_POWER_MAX: 1000,
    CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
    CONF_DURATION_MIN: 0.3,
    CONF_DURATION_STOP_MIN: 0.1,
    CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
    CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
    CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
    CONF_BATTERY_SOC_THRESHOLD: 0,
    CONF_MAX_ON_TIME_PER_DAY_MIN: 60,
    CONF_MIN_ON_TIME_PER_DAY_MIN: 0,
}


async def _setup_device(hass):
    """Creates and returns the ManagedDevice for Equipement A."""
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data=DEVICE_A_DATA,
    )
    device = await create_managed_device(hass, entry_a, "equipement_a")
    assert device is not None

    # Crée l'entité sous-jacente (input_boolean) pour que is_active fonctionne
    await create_test_input_boolean(hass, device.entity_id, "fake underlying A")
    fake_bool = search_entity(hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN)
    assert fake_bool is not None

    return device, fake_bool


# ---------------------------------------------------------------------------
# Test 1 : état initial — pas d'activation forcée
# ---------------------------------------------------------------------------

async def test_timed_activation_initial_state(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """forced_end_time est None par défaut."""
    device, _ = await _setup_device(hass)

    assert device.forced_end_time is None
    assert device.is_enabled is True


# ---------------------------------------------------------------------------
# Test 2 : start_forced sans durée
# ---------------------------------------------------------------------------

async def test_start_forced_no_duration(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """start_forced sans durée désactive SO, allume le device et ne pose pas de timer."""
    device, fake_bool = await _setup_device(hass)

    # On mock activate pour ne pas appeler le service HA réel
    device.activate = AsyncMock()

    await device.start_forced(duration_hours=None)
    await hass.async_block_till_done()

    assert device.is_enabled is False
    assert device.forced_end_time is None
    device.activate.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 3 : start_forced avec durée — forced_end_time dans le futur
# ---------------------------------------------------------------------------

async def test_start_forced_with_duration(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """start_forced(4h) : enable=False, forced_end_time ≈ now+4h."""
    device, _ = await _setup_device(hass)

    device.activate = AsyncMock()
    current_tz = get_tz(hass)
    before = datetime.now(current_tz)

    await device.start_forced(duration_hours=4)
    await hass.async_block_till_done()

    after = datetime.now(current_tz)

    assert device.is_enabled is False
    assert device.forced_end_time is not None
    assert device.forced_end_time > before + timedelta(hours=3, minutes=59)
    assert device.forced_end_time < after + timedelta(hours=4, seconds=2)
    device.activate.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 4 : stop_forced — efface le timer et désactive
# ---------------------------------------------------------------------------

async def test_stop_forced(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """stop_forced efface forced_end_time et désactive le device."""
    device, _ = await _setup_device(hass)

    device.activate = AsyncMock()
    device.deactivate = AsyncMock()

    await device.start_forced(duration_hours=2)
    await hass.async_block_till_done()

    assert device.forced_end_time is not None

    await device.stop_forced()
    await hass.async_block_till_done()

    assert device.forced_end_time is None
    device.deactivate.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 5 : expire_forced_activation — timer pas encore expiré
# ---------------------------------------------------------------------------

async def test_expire_forced_activation_not_yet(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """expire_forced_activation retourne False si le timer n'est pas expiré."""
    device, _ = await _setup_device(hass)

    device.activate = AsyncMock()
    device.deactivate = AsyncMock()

    await device.start_forced(duration_hours=4)
    await hass.async_block_till_done()

    expired = await device.expire_forced_activation()
    assert expired is False
    assert device.forced_end_time is not None
    device.deactivate.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 6 : expire_forced_activation — timer expiré
# ---------------------------------------------------------------------------

async def test_expire_forced_activation_expired(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """expire_forced_activation désactive + re-enable SO quand le timer est expiré."""
    device, _ = await _setup_device(hass)

    device.activate = AsyncMock()
    device.deactivate = AsyncMock()

    # Pose un forced_end_time dans le passé
    current_tz = get_tz(hass)
    device._forced_end_time = datetime.now(current_tz) - timedelta(seconds=1)
    device.set_enable(False)

    expired = await device.expire_forced_activation()
    await hass.async_block_till_done()

    assert expired is True
    assert device.forced_end_time is None
    assert device.is_enabled is True
    device.deactivate.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 7 : expire_forced_activation — aucun timer actif (forced_end_time None)
# ---------------------------------------------------------------------------

async def test_expire_forced_activation_no_timer(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """expire_forced_activation retourne False si aucun timer n'est posé."""
    device, _ = await _setup_device(hass)

    device.deactivate = AsyncMock()

    assert device.forced_end_time is None
    expired = await device.expire_forced_activation()
    assert expired is False
    device.deactivate.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 8 : set_forced_end_time — restauration depuis HA restart (futur)
# ---------------------------------------------------------------------------

async def test_set_forced_end_time_restore_future(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """set_forced_end_time restaure un timer dans le futur sans l'expirer."""
    device, _ = await _setup_device(hass)

    current_tz = get_tz(hass)
    future_time = datetime.now(current_tz) + timedelta(hours=2)
    device.set_forced_end_time(future_time)

    assert device.forced_end_time == future_time

    # expire_forced_activation ne doit pas déclencher l'expiration
    device.deactivate = AsyncMock()
    expired = await device.expire_forced_activation()
    assert expired is False
    device.deactivate.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 9 : set_forced_end_time — restauration depuis HA restart (passé)
# ---------------------------------------------------------------------------

async def test_set_forced_end_time_restore_past(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """set_forced_end_time avec une date passée : expire_forced_activation doit s'arrêter."""
    device, _ = await _setup_device(hass)

    current_tz = get_tz(hass)
    past_time = datetime.now(current_tz) - timedelta(minutes=5)
    device.set_forced_end_time(past_time)
    device.set_enable(False)

    device.deactivate = AsyncMock()
    expired = await device.expire_forced_activation()
    await hass.async_block_till_done()

    assert expired is True
    assert device.forced_end_time is None
    assert device.is_enabled is True
    device.deactivate.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 10 : attribut forced_end_time exposé dans le switch HA
# ---------------------------------------------------------------------------

async def test_switch_attribute_forced_end_time_none(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Sans activation forcée, l'attribut forced_end_time du switch est None."""
    device, _ = await _setup_device(hass)

    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert device_switch is not None

    attrs = device_switch.get_attr_extra_state_attributes
    assert attrs.get("forced_end_time") is None


# ---------------------------------------------------------------------------
# Test 11 : attribut forced_end_time exposé dans le switch HA — activé
# ---------------------------------------------------------------------------

async def test_switch_attribute_forced_end_time_set(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Avec activation forcée, l'attribut forced_end_time du switch est une ISO string."""
    device, _ = await _setup_device(hass)

    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert device_switch is not None

    device.activate = AsyncMock()

    await device.start_forced(duration_hours=1)
    await hass.async_block_till_done()

    # Déclenche la mise à jour des attributs manuellement
    device_switch.update_custom_attributes(device)

    attrs = device_switch.get_attr_extra_state_attributes
    forced_end_time_str = attrs.get("forced_end_time")
    assert forced_end_time_str is not None

    # Doit être parseable en datetime ISO 8601
    parsed = datetime.fromisoformat(forced_end_time_str)
    current_tz = get_tz(hass)
    assert parsed > datetime.now(current_tz)


# ---------------------------------------------------------------------------
# Test 12 : durées valides — 1h, 4h, 12h, 24h
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("duration_hours", [1, 4, 12, 24])
async def test_start_forced_all_valid_durations(
    hass: HomeAssistant, init_solar_optimizer_central_config, duration_hours
):
    """start_forced fonctionne pour toutes les durées admises (1h, 4h, 12h, 24h)."""
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data=DEVICE_A_DATA,
    )
    device = await create_managed_device(hass, entry_a, "equipement_a")
    assert device is not None
    await create_test_input_boolean(hass, device.entity_id, "fake underlying A")

    device.activate = AsyncMock()
    current_tz = get_tz(hass)
    before = datetime.now(current_tz)

    await device.start_forced(duration_hours=duration_hours)
    await hass.async_block_till_done()

    assert device.forced_end_time is not None
    expected_approx = before + timedelta(hours=duration_hours)
    delta = abs((device.forced_end_time - expected_approx).total_seconds())
    assert delta < 5, f"forced_end_time trop éloigné de l'attendu pour {duration_hours}h"
    assert device.is_enabled is False


# ---------------------------------------------------------------------------
# Test 13 : le bouton Enable passe à 'off' lors d'un start_forced
# ---------------------------------------------------------------------------

async def test_enable_switch_turns_off_on_start_forced(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Quand start_forced est appelé, le switch Enable doit passer à 'off'."""
    device, _ = await _setup_device(hass)

    enable_switch = search_entity(
        hass, "switch.enable_solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert enable_switch is not None
    assert enable_switch.state == "on"

    device.activate = AsyncMock()

    await device.start_forced(duration_hours=4)
    await hass.async_block_till_done()

    assert device.is_enabled is False
    assert enable_switch.state == "off"


# ---------------------------------------------------------------------------
# Test 14 : le bouton Enable repasse à 'on' après expiration du timer
# ---------------------------------------------------------------------------

async def test_enable_switch_turns_on_after_timer_expiry(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Quand le timer expire, le switch Enable doit repasser à 'on'."""
    device, _ = await _setup_device(hass)

    enable_switch = search_entity(
        hass, "switch.enable_solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert enable_switch is not None

    device.activate = AsyncMock()
    device.deactivate = AsyncMock()

    # Pose un forced_end_time déjà expiré
    current_tz = get_tz(hass)
    device._forced_end_time = datetime.now(current_tz) - timedelta(seconds=1)
    device.set_enable(False)
    await hass.async_block_till_done()

    assert enable_switch.state == "off"

    # Simule l'expiration (appelée par le coordinator)
    expired = await device.expire_forced_activation()
    await hass.async_block_till_done()

    assert expired is True
    assert device.is_enabled is True
    assert enable_switch.state == "on"


# ---------------------------------------------------------------------------
# Test 15 : stop_forced repasse le bouton Enable à 'on'
# ---------------------------------------------------------------------------

async def test_enable_switch_turns_on_after_stop_forced(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Quand stop_forced est appelé, SO est désactivé (enable reste off), pas remis on."""
    device, _ = await _setup_device(hass)

    enable_switch = search_entity(
        hass, "switch.enable_solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert enable_switch is not None

    device.activate = AsyncMock()
    device.deactivate = AsyncMock()

    await device.start_forced(duration_hours=2)
    await hass.async_block_till_done()
    assert enable_switch.state == "off"

    # STOP ne remet pas enable à True — c'est à l'utilisateur de le faire
    await device.stop_forced()
    await hass.async_block_till_done()

    assert device.forced_end_time is None
    assert device.is_enabled is False
    assert enable_switch.state == "off"


# ---------------------------------------------------------------------------
# Test 16 : désactivation du device switch pendant une activation forcée → timer annulé
# ---------------------------------------------------------------------------

async def test_device_stop_clears_forced_timer(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Quand le device switch est éteint (STOP), le timer forcé doit être annulé."""
    device, fake_bool = await _setup_device(hass)

    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert device_switch is not None

    device.activate = AsyncMock()
    device.deactivate = AsyncMock()

    # Démarre l'activation forcée (pose un timer)
    await device.start_forced(duration_hours=4)
    await hass.async_block_till_done()

    assert device.is_enabled is False
    assert device.forced_end_time is not None

    # Simule un clic STOP sur le device switch
    device_switch._attr_is_on = True  # on force l'état pour déclencher async_turn_off
    await device_switch.async_turn_off()
    await hass.async_block_till_done()

    assert device.forced_end_time is None
    device.deactivate.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 17 : clic Enable (turn_on) pendant activation forcée → ne touche pas au timer
# ---------------------------------------------------------------------------

async def test_enable_turn_on_does_not_clear_timer(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Re-activer Enable ne doit PAS annuler le timer (c'est l'arrêt du device qui le fait)."""
    device, _ = await _setup_device(hass)

    enable_switch = search_entity(
        hass, "switch.enable_solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert enable_switch is not None

    device.activate = AsyncMock()

    await device.start_forced(duration_hours=4)
    await hass.async_block_till_done()

    assert device.forced_end_time is not None

    # L'utilisateur re-clique Enable → SO reprend la main mais le timer reste
    await enable_switch.async_turn_on()
    await hass.async_block_till_done()

    assert device.is_enabled is True
    # Le timer est toujours là — c'est l'arrêt du device qui l'annulera
    assert device.forced_end_time is not None


# ---------------------------------------------------------------------------
# Test 18 : le coordinator éteint le device → timer annulé
# ---------------------------------------------------------------------------

async def test_coordinator_deactivate_clears_forced_timer(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Quand SO reprend la main et éteint le device via deactivate(),
    le timer forcé doit être annulé et l'attribut HA mis à jour."""
    device, _ = await _setup_device(hass)

    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert device_switch is not None

    device.activate = AsyncMock()

    # Démarre l'activation forcée
    await device.start_forced(duration_hours=4)
    await hass.async_block_till_done()

    assert device.forced_end_time is not None
    assert device.is_enabled is False

    # Simule le coordinator qui reprend la main : il appelle deactivate() directement
    await device.deactivate()
    await hass.async_block_till_done()

    # Le timer doit être annulé
    assert device.forced_end_time is None

    # L'attribut du switch HA doit refléter forced_end_time=None
    attrs = device_switch.get_attr_extra_state_attributes
    assert attrs.get("forced_end_time") is None
