"""Number entities for the adjustable values."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PvSurplusEntity

PRICE_UNIT = "ct/kWh"


@dataclass(frozen=True)
class Spec:
    key: str
    minimum: float
    maximum: float
    step: float
    unit: str | None
    group: str  # base | forecast | compressor | price | price_any | price_comp | peak


SPECS: list[Spec] = [
    Spec("on_threshold_w", 200, 10000, 50, UnitOfPower.WATT, "base"),
    Spec("off_threshold_w", -5000, 0, 50, UnitOfPower.WATT, "base"),
    Spec("on_delay_min", 0, 60, 1, UnitOfTime.MINUTES, "base"),
    Spec("off_delay_min", 0, 60, 1, UnitOfTime.MINUTES, "base"),
    Spec("soc_release", 0, 100, 1, PERCENTAGE, "base"),
    Spec("soc_stop", 0, 100, 1, PERCENTAGE, "base"),
    Spec("min_runtime_min", 10, 240, 5, UnitOfTime.MINUTES, "base"),
    Spec("lock_min", 0, 720, 5, UnitOfTime.MINUTES, "base"),
    Spec("max_activations", 1, 10, 1, None, "base"),
    Spec("soc_forecast", 0, 100, 1, PERCENTAGE, "forecast"),
    Spec("battery_capacity_kwh", 0.5, 100, 0.5, UnitOfEnergy.KILO_WATT_HOUR, "forecast"),
    Spec("forecast_reserve_kwh", 0, 50, 0.5, UnitOfEnergy.KILO_WATT_HOUR, "forecast"),
    Spec("comp_min_kw", 0.5, 10, 0.1, UnitOfPower.KILO_WATT, "compressor"),
    Spec("comp_max_kw", 0.5, 10, 0.1, UnitOfPower.KILO_WATT, "compressor"),
    Spec("comp_reserve_kw", 0, 2, 0.1, UnitOfPower.KILO_WATT, "compressor"),
    Spec("comp_step_kw", 0.1, 1, 0.1, UnitOfPower.KILO_WATT, "compressor"),
    Spec("comp_interval_min", 1, 60, 1, UnitOfTime.MINUTES, "compressor"),
    Spec("price_cheap_ct", -50, 100, 0.5, PRICE_UNIT, "price"),
    Spec("price_expensive_ct", -50, 200, 0.5, PRICE_UNIT, "price_any"),
    Spec("price_comp_kw", 0.5, 10, 0.1, UnitOfPower.KILO_WATT, "price_comp"),
    Spec("peak_factor_pct", 100, 200, 1, PERCENTAGE, "peak"),
    Spec("peak_soc_margin", 0, 50, 1, PERCENTAGE, "peak"),
    Spec("peak_import_min", 0, 60, 1, UnitOfTime.MINUTES, "peak"),
    Spec("peak_max_duration_min", 10, 480, 5, UnitOfTime.MINUTES, "peak"),
    Spec("peak_lock_min", 0, 720, 5, UnitOfTime.MINUTES, "peak"),
    Spec("peak_max_per_day", 1, 10, 1, None, "peak"),
]
PRICE_GROUPS = {"price", "price_any", "price_comp", "peak"}


def groups(c) -> set[str]:
    out = {"base"}
    if c.has_forecast:
        out.add("forecast")
    if c.has_compressor_control:
        out.add("compressor")
    if c.has_price:
        out.add("price")
        if c.has_compressor_control:
            out.add("price_comp")
    if c.has_price_settings:
        out.add("price_any")
    if c.has_peak:
        out.add("peak")
    return out


def keys(c) -> list[str]:
    active = groups(c)
    return [spec.key for spec in SPECS if spec.group in active]


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    c = entry.runtime_data
    active = groups(c)
    async_add_entities(SettingNumber(c, spec) for spec in SPECS if spec.group in active)


class SettingNumber(PvSurplusEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, controller, spec: Spec) -> None:
        super().__init__(controller, spec.key)
        self._attr_native_min_value = spec.minimum
        self._attr_native_max_value = spec.maximum
        self._attr_native_step = spec.step
        self._attr_native_unit_of_measurement = spec.unit
        self._price = spec.group in PRICE_GROUPS

    @property
    def available(self) -> bool:
        # Price settings can only be changed while the price control is switched on.
        return not self._price or bool(self.controller.settings.price_control)

    @property
    def native_value(self) -> float:
        return float(getattr(self.controller.settings, self.key))

    async def async_set_native_value(self, value: float) -> None:
        self.controller.update_setting(self.key, float(value))
        self.async_write_ha_state()
