"""Switches: observe mode, compressor control, forecast use."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PvSurplusEntity


def keys(c) -> list[str]:
    out = ["observe"]
    if c.has_compressor_control:
        out.append("dynamic_power")
    if c.has_forecast:
        out.append("use_forecast")
    if c.has_price_settings:
        out.append("price_control")
    if c.has_price:
        out.append("price_stop_expensive")
    return out


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    c = entry.runtime_data
    async_add_entities(SettingSwitch(c, key) for key in keys(c))


class SettingSwitch(PvSurplusEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        # The stop option belongs to the price control and is locked while it is off.
        if self.key == "price_stop_expensive":
            return bool(self.controller.settings.price_control)
        return True

    @property
    def is_on(self) -> bool:
        return bool(getattr(self.controller.settings, self.key))

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.controller.update_setting(self.key, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.controller.update_setting(self.key, False)
        self.async_write_ha_state()
