"""End-to-end tests: config flow, entities, price lock, control loop, cleanup."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from homeassistant import config_entries
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.emsesp_pv_surplus.const import DOMAIN

from .conftest import BATTERY, GRID, PRICE, PRICE_NO_UNIT, SIGNAL, SOC

BASE = {
    "signal_entity": SIGNAL,
    "signal_bit": 0,
    "grid_entity": GRID,
    "grid_sign": "import_positive",
    "battery_power_entity": BATTERY,
    "battery_sign": "discharge_positive",
    "soc_entity": SOC,
    "price_unit": "auto",
}

PRICE_KEYS = ["price_control", "price_block_start", "price_stop_expensive", "price_cheap_ct", "price_expensive_ct"]


async def _setup(hass: HomeAssistant, **extra) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="WP", data={"name": "WP", **BASE, **extra}, unique_id=SIGNAL)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _eid(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")


async def test_config_flow_without_price(hass: HomeAssistant, sources) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "WP", **BASE})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["price_entity"] is None
    assert result["data"]["price_unit"] == "auto"
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(result["result"].entry_id)


async def test_config_flow_price_unit_check(hass: HomeAssistant, sources) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "WP", **BASE, "price_entity": PRICE_NO_UNIT}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"price_unit": "price_unit_unknown"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "WP", **BASE, "price_entity": PRICE_NO_UNIT, "price_unit": "minor_kwh"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["price_unit"] == "minor_kwh"
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(result["result"].entry_id)


async def test_config_flow_recognised_price_unit(hass: HomeAssistant, sources) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "WP", **BASE, "price_entity": PRICE}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(result["result"].entry_id)


async def test_setup_without_price_has_no_price_entities(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass)
    for key in PRICE_KEYS:
        assert _eid(hass, entry, "switch", key) is None
        assert _eid(hass, entry, "number", key) is None
    status = hass.states.get(_eid(hass, entry, "sensor", "status"))
    assert status is not None
    assert "price" not in status.attributes["checks"]
    assert status.attributes["price"] is False
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_price_settings_locked_until_switch_on(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass, price_entity=PRICE)
    controller = entry.runtime_data
    switch = _eid(hass, entry, "switch", "price_control")
    cheap = _eid(hass, entry, "number", "price_cheap_ct")
    stop = _eid(hass, entry, "switch", "price_stop_expensive")
    assert hass.states.get(switch).state == "off"
    assert hass.states.get(cheap).state == STATE_UNAVAILABLE
    assert hass.states.get(stop).state == STATE_UNAVAILABLE

    # Locked: the call is ignored by Home Assistant, the value does not change
    await hass.services.async_call("number", "set_value", {"entity_id": cheap, "value": 20}, blocking=True)
    assert controller.settings.price_cheap_ct == 15.0

    await hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(cheap).state == "15.0"
    assert hass.states.get(stop).state == "off"
    await hass.services.async_call("number", "set_value", {"entity_id": cheap, "value": 20}, blocking=True)
    assert controller.settings.price_cheap_ct == 20.0
    assert hass.states.get(cheap).state == "20.0"

    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(cheap).state == STATE_UNAVAILABLE
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_cheap_price_starts_pv_mode(hass: HomeAssistant, sources) -> None:
    calls = async_mock_service(hass, "text", "set_value")
    entry = await _setup(hass, price_entity=PRICE)
    controller = entry.runtime_data
    status_id = _eid(hass, entry, "sensor", "status")

    # 24.31 ct with default thresholds 15/35: normal price, no start
    await hass.services.async_call("switch", "turn_on", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    attrs = hass.states.get(status_id).attributes
    assert attrs["price_ct"] == 24.31
    assert "price" not in attrs["checks"]  # start block switch is off by default
    assert attrs["requested"] is False

    # Cheap: starts, but observe mode (default) writes nothing
    hass.states.async_set(PRICE, "0.1184", {"unit_of_measurement": "EUR/kWh"})
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    state = hass.states.get(status_id)
    assert state.state == "price_cheap"
    assert state.attributes["run_kind"] == "cheap"
    assert calls == []

    # Observe off: the PV bit is written
    await hass.services.async_call("switch", "turn_off", {"entity_id": _eid(hass, entry, "switch", "observe")}, blocking=True)
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    assert calls
    assert calls[-1].data == {"entity_id": SIGNAL, "value": "100000100000"}
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_expensive_blocks_start(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass, price_entity=PRICE)
    controller = entry.runtime_data
    status_id = _eid(hass, entry, "sensor", "status")
    await hass.services.async_call("switch", "turn_on", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
    hass.states.async_set(PRICE, "0.45", {"unit_of_measurement": "EUR/kWh"})
    hass.states.async_set(GRID, "-3000", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    state = hass.states.get(status_id)
    assert "price" not in state.attributes["checks"]  # off by default (issue #6)
    assert state.attributes["price_expensive"] is True

    block_id = _eid(hass, entry, "switch", "price_block_start")
    assert hass.states.get(block_id).state == "off"
    await hass.services.async_call("switch", "turn_on", {"entity_id": block_id}, blocking=True)
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    state = hass.states.get(status_id)
    assert state.attributes["checks"]["price"] is False
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_unknown_unit_pauses_price(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass, price_entity=PRICE_NO_UNIT)  # auto mode, sensor without unit
    controller = entry.runtime_data
    await hass.services.async_call("switch", "turn_on", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
    await hass.services.async_call("switch", "turn_on", {"entity_id": _eid(hass, entry, "switch", "price_block_start")}, blocking=True)
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    attrs = hass.states.get(_eid(hass, entry, "sensor", "status")).attributes
    assert attrs["price_state"] == "unit_unknown"
    assert attrs["price_ct"] is None
    assert attrs["checks"]["price"] is True  # never blocks on an unknown unit
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_removing_price_sensor_cleans_up(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass, price_entity=PRICE)
    assert _eid(hass, entry, "switch", "price_control") is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result["flow_id"], dict(BASE))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    for key in PRICE_KEYS:
        assert _eid(hass, entry, "switch", key) is None
        assert _eid(hass, entry, "number", key) is None
    assert _eid(hass, entry, "sensor", "status") is not None
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_settings_survive_reload(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass, price_entity=PRICE)
    await hass.services.async_call("switch", "turn_on", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
    await hass.services.async_call(
        "number", "set_value", {"entity_id": _eid(hass, entry, "number", "price_expensive_ct"), "value": 41.5}, blocking=True
    )
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    controller = entry.runtime_data
    assert controller.settings.price_control is True
    assert controller.settings.price_expensive_ct == 41.5
    assert await hass.config_entries.async_unload(entry.entry_id)
