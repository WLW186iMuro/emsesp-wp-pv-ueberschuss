"""End-to-end tests: config flow, entities, price lock, control loop, cleanup."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from homeassistant import config_entries
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.emsesp_pv_surplus.const import DOMAIN

from datetime import timedelta

from homeassistant.util import dt as dt_util

from .conftest import AVERAGE, BATTERY, EVU, GRID, HOURLY, PRICE, PRICE_NO_UNIT, RESERVE, SIGNAL, SOC

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

PRICE_KEYS = ["price_control", "price_stop_expensive", "price_cheap_ct", "price_expensive_ct"]


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
    assert attrs["checks"]["price"] is True
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
    await hass.services.async_call("switch", "turn_on", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
    hass.states.async_set(PRICE, "0.45", {"unit_of_measurement": "EUR/kWh"})
    hass.states.async_set(GRID, "-3000", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    state = hass.states.get(_eid(hass, entry, "sensor", "status"))
    assert state.attributes["checks"]["price"] is False
    assert state.attributes["price_expensive"] is True
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_unknown_unit_pauses_price(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass, price_entity=PRICE_NO_UNIT)  # auto mode, sensor without unit
    controller = entry.runtime_data
    await hass.services.async_call("switch", "turn_on", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
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


PEAK = {
    "evu_entity": EVU,
    "backup_reserve_entity": RESERVE,
    "hourly_price_entity": HOURLY,
    "avg_price_entity": AVERAGE,
}
PEAK_NUMBERS = ["peak_factor_pct", "peak_soc_margin", "peak_import_min", "peak_max_duration_min", "peak_lock_min", "peak_max_per_day"]


async def test_config_flow_peak_needs_all_fields(hass: HomeAssistant, sources) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "WP", **BASE, "evu_entity": EVU, "hourly_price_entity": HOURLY}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        "backup_reserve_entity": "peak_incomplete",
        "avg_price_entity": "peak_incomplete",
    }
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "WP", **BASE, **PEAK})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["evu_entity"] == EVU
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(result["result"].entry_id)


async def test_peak_entities_without_price_sensor(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass, **PEAK)
    assert _eid(hass, entry, "switch", "price_control") is not None
    assert _eid(hass, entry, "number", "price_expensive_ct") is not None
    assert _eid(hass, entry, "number", "price_cheap_ct") is None
    assert _eid(hass, entry, "switch", "price_stop_expensive") is None
    for key in PEAK_NUMBERS:
        assert hass.states.get(_eid(hass, entry, "number", key)).state == STATE_UNAVAILABLE
    assert _eid(hass, entry, "binary_sensor", "peak_active") is not None
    assert _eid(hass, entry, "sensor", "peak_activations_today") is not None
    attrs = hass.states.get(_eid(hass, entry, "sensor", "status")).attributes
    assert attrs["peak"] is True
    assert "price_control" not in attrs["peak_checks"]
    assert attrs["peak_price_ct"] == 24.31
    assert attrs["avg_price_ct"] == 22.1
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_without_peak_no_peak_entities(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass)
    assert _eid(hass, entry, "switch", "price_control") is None
    assert _eid(hass, entry, "binary_sensor", "peak_active") is None
    for key in PEAK_NUMBERS:
        assert _eid(hass, entry, "number", key) is None
    attrs = hass.states.get(_eid(hass, entry, "sensor", "status")).attributes
    assert attrs["peak"] is False
    assert "peak_checks" not in attrs
    assert await hass.config_entries.async_unload(entry.entry_id)


async def _peak_ready(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Price clearly above the average, battery at the reserve, grid import for 11 min."""
    await hass.services.async_call("switch", "turn_on", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
    hass.states.async_set(GRID, "1500", {"unit_of_measurement": "W"})
    hass.states.async_set(SOC, "21", {"unit_of_measurement": "%"})
    hass.states.async_set(HOURLY, "0.41", {"unit_of_measurement": "EUR/kWh"})
    await hass.async_block_till_done()
    entry.runtime_data.state.peak_import_since = dt_util.now() - timedelta(minutes=11)


async def test_peak_sets_and_lifts_evu_bit(hass: HomeAssistant, sources) -> None:
    calls = async_mock_service(hass, "text", "set_value")
    entry = await _setup(hass, **PEAK)
    controller = entry.runtime_data
    status_id = _eid(hass, entry, "sensor", "status")
    await _peak_ready(hass, entry)

    # Observe mode (default): status shows the block, nothing is written
    await controller._async_tick()
    await hass.async_block_till_done()
    state = hass.states.get(status_id)
    assert state.state == "peak_block"
    assert state.attributes["peak_checks"]["no_surplus"] is True
    assert calls == []

    # Observe off: only the first bit of the EVU input changes, the PV input stays as it is
    await hass.services.async_call("switch", "turn_off", {"entity_id": _eid(hass, entry, "switch", "observe")}, blocking=True)
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    evu_calls = [c for c in calls if c.data["entity_id"] == EVU]
    assert evu_calls[-1].data == {"entity_id": EVU, "value": "100000000001010"}
    assert all(c.data["entity_id"] != SIGNAL or c.data["value"][0] == "0" for c in calls)
    hass.states.async_set(EVU, "100000000001010")
    assert hass.states.get(_eid(hass, entry, "binary_sensor", "peak_active")).state == "on"

    # Switching the price control off lifts the block at once
    await hass.services.async_call("switch", "turn_off", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    assert calls[-1].data == {"entity_id": EVU, "value": "000000000001010"}
    assert controller.state.peak_active is False
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_removing_entry_lifts_evu_block(hass: HomeAssistant, sources) -> None:
    calls = async_mock_service(hass, "text", "set_value")
    entry = await _setup(hass, **PEAK)
    await hass.services.async_call("switch", "turn_off", {"entity_id": _eid(hass, entry, "switch", "observe")}, blocking=True)
    await _peak_ready(hass, entry)
    await entry.runtime_data._async_tick()
    await hass.async_block_till_done()
    hass.states.async_set(EVU, "100000000001010")
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert calls[-1].data == {"entity_id": EVU, "value": "000000000001010"}


async def test_observe_mode_logs_peak(hass: HomeAssistant, sources) -> None:
    calls = async_mock_service(hass, "text", "set_value")
    logbook = async_mock_service(hass, "logbook", "log")
    entry = await _setup(hass, **PEAK)
    controller = entry.runtime_data
    await _peak_ready(hass, entry)
    await controller._async_tick()
    await hass.async_block_till_done()
    messages = [c.data["message"] for c in logbook]
    assert "[Observe] would set EVU block (price high, battery empty)" in messages
    await hass.services.async_call("switch", "turn_off", {"entity_id": _eid(hass, entry, "switch", "price_control")}, blocking=True)
    await hass.async_block_till_done()
    await controller._async_tick()
    await hass.async_block_till_done()
    messages = [c.data["message"] for c in logbook]
    assert "[Observe] would lift EVU block (price control off or mode not automatic)" in messages
    assert logbook[-1].data["entity_id"] == _eid(hass, entry, "sensor", "status")
    assert calls == []
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_evu_bit_position(hass: HomeAssistant, sources) -> None:
    calls = async_mock_service(hass, "text", "set_value")
    entry = await _setup(hass, **PEAK, evu_bit=2)
    await hass.services.async_call("switch", "turn_off", {"entity_id": _eid(hass, entry, "switch", "observe")}, blocking=True)
    await _peak_ready(hass, entry)
    await entry.runtime_data._async_tick()
    await hass.async_block_till_done()
    assert calls[-1].data == {"entity_id": EVU, "value": "001000000001010"}
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_config_flow_stores_evu_bit(hass: HomeAssistant, sources) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "WP", **BASE, **PEAK, "evu_bit": 4.0}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["evu_bit"] == 4
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(result["result"].entry_id)


async def test_buttons_reset_evu_lock_and_counter(hass: HomeAssistant, sources) -> None:
    entry = await _setup(hass, **PEAK)
    controller = entry.runtime_data
    controller.state.last_off = dt_util.now()
    controller.state.activations = 2
    controller.state.peak_last_end = dt_util.now()
    controller.state.peak_count = 2
    await hass.services.async_call("button", "press", {"entity_id": _eid(hass, entry, "button", "reset_lock")}, blocking=True)
    await hass.services.async_call("button", "press", {"entity_id": _eid(hass, entry, "button", "reset_counter")}, blocking=True)
    await hass.async_block_till_done()
    assert controller.state.last_off is None
    assert controller.state.peak_last_end is None
    assert controller.state.activations == 0
    assert controller.state.peak_count == 0
    assert hass.states.get(_eid(hass, entry, "sensor", "peak_activations_today")).state == "0"
    assert await hass.config_entries.async_unload(entry.entry_id)
