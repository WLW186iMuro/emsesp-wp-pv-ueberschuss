"""EMS-ESP PV surplus control for heat pumps (SG Ready / PV input via EMS-ESP)."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    CARD_FILE,
    CONF_EVU_BIT,
    CONF_EVU_ENTITY,
    CONF_SIGNAL_BIT,
    CONF_SIGNAL_ENTITY,
    DOMAIN,
    FRONTEND_URL,
    PLATFORMS,
)
from .controller import STORAGE_VERSION, PvSurplusController
from .logic import set_bit, valid_bits

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type PvSurplusConfigEntry = ConfigEntry[PvSurplusController]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard card and make every dashboard load it."""
    path = Path(__file__).parent / CARD_FILE

    def _hash() -> str:
        return hashlib.sha1(path.read_bytes()).hexdigest()[:10]

    version = await hass.async_add_executor_job(_hash)
    url = f"{FRONTEND_URL}?v={version}"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL, str(path), False)]
    )
    # A Lovelace resource is loaded before cards are created. An extra JS URL is
    # a bare import() in the index page that the frontend's service worker can
    # serve from cache without it (home-assistant/frontend#18728), leaving the
    # card on "configuration error". Use the resource when dashboards are in
    # storage mode. Lovelace data may not exist yet during startup.
    async def _publish(_hass: HomeAssistant) -> None:
        if not await _async_register_resource(hass, url):
            add_extra_js_url(hass, url)

    async_at_started(hass, _publish)
    return True


async def _async_register_resource(hass: HomeAssistant, url: str) -> bool:
    """Create or update the Lovelace resource for the card. False if not possible."""
    try:
        lovelace = hass.data.get("lovelace")
        if isinstance(lovelace, dict):
            resources = lovelace.get("resources")
            mode = lovelace.get("resource_mode") or lovelace.get("mode")
        else:
            resources = getattr(lovelace, "resources", None)
            mode = getattr(lovelace, "resource_mode", None) or getattr(lovelace, "mode", None)
        if resources is None or mode != "storage" or not hasattr(resources, "async_create_item"):
            return False
        if not getattr(resources, "loaded", True):
            await resources.async_load()
            resources.loaded = True
        for item in resources.async_items():
            if str(item.get("url", "")).split("?")[0] == FRONTEND_URL:
                if item.get("url") != url:
                    await resources.async_update_item(item["id"], {"res_type": "module", "url": url})
                return True
        await resources.async_create_item({"res_type": "module", "url": url})
        return True
    except Exception as err:  # noqa: BLE001 - fall back to extra JS URL
        _LOGGER.warning("Could not register dashboard resource, using extra JS URL: %s", err)
        return False


async def async_setup_entry(hass: HomeAssistant, entry: PvSurplusConfigEntry) -> bool:
    controller = PvSurplusController(hass, entry)
    await controller.async_load()
    entry.runtime_data = controller
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_remove_stale_entities(hass, entry, controller)
    await controller.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


def _expected_keys(controller: PvSurplusController) -> set[str]:
    from . import binary_sensor, button, number, select, sensor, switch, time  # noqa: PLC0415

    keys: set[str] = set()
    for module in (binary_sensor, button, number, select, sensor, switch, time):
        keys.update(module.keys(controller))
    return keys


def _async_remove_stale_entities(
    hass: HomeAssistant, entry: ConfigEntry, controller: PvSurplusController
) -> None:
    """Remove entities of optional features that are no longer configured.

    Without this they would stay behind as "no longer provided" after e.g. the
    forecast or price sensor has been removed in the options.
    """
    expected = {f"{entry.entry_id}_{key}" for key in _expected_keys(controller)}
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id not in expected:
            _LOGGER.debug("Removing stale entity %s", reg_entry.entity_id)
            registry.async_remove(reg_entry.entity_id)


async def _async_update_listener(hass: HomeAssistant, entry: PvSurplusConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PvSurplusConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Hand the heat pump back to normal mode and delete stored data."""
    store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
    data = await store.async_load() or {}
    cfg = {**entry.data, **entry.options}
    requested = (data.get("state") or {}).get("requested")
    observe = (data.get("settings") or {}).get("observe", True)
    entity_id = cfg.get(CONF_SIGNAL_ENTITY)
    bit = int(cfg.get(CONF_SIGNAL_BIT) or 0)
    st = hass.states.get(entity_id) if entity_id else None
    if requested and not observe and st and valid_bits(st.state, bit) and st.state[bit] == "1":
        try:
            await hass.services.async_call(
                "text",
                "set_value",
                {"entity_id": entity_id, "value": set_bit(st.state, bit, False)},
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Could not reset %s: %s", entity_id, err)
    # Lift an EVU block we set (also in observe mode, see controller)
    evu_written = (data.get("state") or {}).get("evu_written")
    evu_id = cfg.get(CONF_EVU_ENTITY)
    evu = hass.states.get(evu_id) if evu_id else None
    evu_bit = int(cfg.get(CONF_EVU_BIT) or 0)
    if evu_written and evu and valid_bits(evu.state, evu_bit) and evu.state[evu_bit] == "1":
        try:
            await hass.services.async_call(
                "text",
                "set_value",
                {"entity_id": evu_id, "value": set_bit(evu.state, evu_bit, False)},
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Could not reset %s: %s", evu_id, err)
    await store.async_remove()
