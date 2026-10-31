"""Selects: mode (automatic / off / manual), §14a control type."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PvSurplusEntity
from .logic import MODES, THROTTLE_CONTROLS


def keys(c) -> list[str]:
    out = ["mode"]
    if c.has_throttle:
        out.append("throttle_control")
    return out


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    c = entry.runtime_data
    entities: list[SelectEntity] = [ModeSelect(c)]
    if c.has_throttle:
        entities.append(ThrottleControlSelect(c))
    async_add_entities(entities)


class ModeSelect(PvSurplusEntity, SelectEntity):
    _attr_options = MODES

    def __init__(self, controller) -> None:
        super().__init__(controller, "mode")

    @property
    def current_option(self) -> str:
        return self.controller.settings.mode

    async def async_select_option(self, option: str) -> None:
        self.controller.update_setting("mode", option)
        self.async_write_ha_state()


class ThrottleControlSelect(PvSurplusEntity, SelectEntity):
    """How the grid operator controls the devices: via the EMS (EEBUS) or directly (relay)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = THROTTLE_CONTROLS

    def __init__(self, controller) -> None:
        super().__init__(controller, "throttle_control")

    @property
    def current_option(self) -> str:
        return self.controller.settings.throttle_control

    async def async_select_option(self, option: str) -> None:
        self.controller.update_setting("throttle_control", option)
        self.async_write_ha_state()
