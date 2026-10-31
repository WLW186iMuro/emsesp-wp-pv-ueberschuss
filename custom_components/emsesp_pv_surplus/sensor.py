"""Sensors: status and live values."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PvSurplusEntity
from .logic import CHECK_KEYS, STATUS_OPTIONS


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _r(value, digits: int = 0):
    if value is None:
        return None
    return round(value, digits) if digits else int(round(value))


def keys(c) -> list[str]:
    out = ["status", "available_power", "activations_today", "runtime_today", "lock_until"]
    if c.has_compressor_control:
        out += ["power_budget", "compressor_target"]
    return out


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    c = entry.runtime_data
    classes = {
        "status": StatusSensor,
        "available_power": AvailablePowerSensor,
        "activations_today": ActivationsSensor,
        "runtime_today": RuntimeSensor,
        "lock_until": LockUntilSensor,
        "power_budget": BudgetSensor,
        "compressor_target": CompressorTargetSensor,
    }
    async_add_entities(classes[key](c) for key in keys(c))


class StatusSensor(PvSurplusEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _unrecorded_attributes = frozenset(
        {
            "checks",
            "grid_w",
            "battery_w",
            "soc",
            "hp_power_w",
            "pvmaxcomp_kw",
            "forecast_remaining_kwh",
            "forecast_30min_w",
            "battery_missing_kwh",
            "budget_avg_w",
            "available_w",
            "comp_target_kw",
            "surplus_since",
            "deficit_since",
            "min_runtime_until",
            "lock_until",
            "last_message",
            "last_message_at",
            "signal_bits",
            "max_activations",
            "price_ct",
            "price_raw",
            "price_unit",
            "price_state",
            "price_cheap",
            "price_expensive",
            "price_cheap_ct",
            "price_expensive_ct",
            "run_kind",
            "hp_idle_since",
        }
    )

    def __init__(self, controller) -> None:
        super().__init__(controller, "status")

    @property
    def native_value(self) -> str | None:
        res = self.controller.result
        return res.status if res else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.controller
        res, inp, st, s = c.result, c.inputs, c.state, c.settings
        attrs: dict[str, Any] = {
            "mode": s.mode,
            "observe": s.observe,
            "requested": st.requested,
            "activations": st.activations,
            "max_activations": int(s.max_activations),
            "last_action": st.last_action,
            "last_action_at": _iso(st.last_action_at),
            "last_message": c.last_message,
            "last_message_at": _iso(c.last_message_at),
            "compressor_control": c.has_compressor_control,
            "forecast": c.has_forecast,
            "price": c.has_price,
            "price_control": s.price_control,
            "price_state": c.price_state,
            "price_cheap_ct": s.price_cheap_ct,
            "price_expensive_ct": s.price_expensive_ct,
        }
        if res is None or inp is None:
            return attrs
        attrs.update(
            {
                "checks": {k: res.checks[k] for k in CHECK_KEYS if k in res.checks},
                "run_kind": res.run_kind,
                "hp_idle_since": _iso(res.hp_idle_since),
                "price_ct": _r(res.price_ct, 2),
                "price_cheap": res.price_cheap,
                "price_expensive": res.price_expensive,
                "price_raw": c.price_raw,
                "price_unit": c.price_unit,
                "available_w": _r(res.available_w),
                "budget_avg_w": _r(res.budget_avg_w),
                "battery_release": res.battery_release,
                "battery_missing_kwh": _r(res.battery_missing_kwh, 2),
                "signal_active": res.signal_active,
                "signal_desired": res.desired_signal,
                "signal_bits": inp.signal_bits,
                "comp_target_kw": res.comp_target_kw,
                "grid_w": _r(inp.grid_w),
                "battery_w": _r(inp.battery_w),
                "soc": inp.soc,
                "hp_power_w": _r(inp.hp_power_w),
                "pvmaxcomp_kw": inp.pvmaxcomp_kw,
                "forecast_remaining_kwh": _r(inp.forecast_remaining_kwh, 2),
                "forecast_30min_w": _r(inp.forecast_30min_w),
                "sun_up": inp.sun_up,
                "lock_until": _iso(res.lock_until),
                "min_runtime_until": _iso(res.min_runtime_until),
                "requested_since": _iso(st.requested_since),
                "surplus_since": _iso(res.surplus_since),
                "deficit_since": _iso(res.deficit_since),
            }
        )
        return attrs


class AvailablePowerSensor(PvSurplusEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, controller) -> None:
        super().__init__(controller, "available_power")

    @property
    def native_value(self):
        res = self.controller.result
        return _r(res.available_w) if res else None


class BudgetSensor(PvSurplusEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, controller) -> None:
        super().__init__(controller, "power_budget")

    @property
    def native_value(self):
        res = self.controller.result
        return _r(res.budget_avg_w) if res else None


class CompressorTargetSensor(PvSurplusEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_suggested_display_precision = 1

    def __init__(self, controller) -> None:
        super().__init__(controller, "compressor_target")

    @property
    def native_value(self):
        res = self.controller.result
        return res.comp_target_kw if res else None


class ActivationsSensor(PvSurplusEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, controller) -> None:
        super().__init__(controller, "activations_today")

    @property
    def native_value(self):
        return self.controller.state.activations


class RuntimeSensor(PvSurplusEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0

    def __init__(self, controller) -> None:
        super().__init__(controller, "runtime_today")

    @property
    def native_value(self):
        return round(self.controller.state.runtime_s / 60.0, 1)


class LockUntilSensor(PvSurplusEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, controller) -> None:
        super().__init__(controller, "lock_until")

    @property
    def native_value(self):
        res = self.controller.result
        return res.lock_until if res else None
