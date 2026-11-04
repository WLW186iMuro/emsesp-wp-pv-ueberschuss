"""Binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PvSurplusEntity


def keys(c) -> list[str]:
    out = ["requested", "signal_active", "battery_release", "surplus"]
    if c.has_peak:
        out += ["peak_active", "evu_signal_active"]
    return out


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    c = entry.runtime_data
    classes = {
        "requested": RequestedSensor,
        "signal_active": SignalSensor,
        "battery_release": ReleaseSensor,
        "surplus": SurplusSensor,
        "peak_active": PeakSensor,
        "evu_signal_active": EvuSignalSensor,
    }
    async_add_entities(classes[key](c) for key in keys(c))


class RequestedSensor(PvSurplusEntity, BinarySensorEntity):
    """PV mode requested by the controller (also in observe mode)."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, controller) -> None:
        super().__init__(controller, "requested")

    @property
    def is_on(self) -> bool:
        return self.controller.state.requested


class SignalSensor(PvSurplusEntity, BinarySensorEntity):
    """PV bit actually set at the heat pump (read back from EMS-ESP)."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, controller) -> None:
        super().__init__(controller, "signal_active")

    @property
    def is_on(self) -> bool | None:
        res = self.controller.result
        return res.signal_active if res else None

    @property
    def available(self) -> bool:
        res = self.controller.result
        return res is not None and res.signal_active is not None


class ReleaseSensor(PvSurplusEntity, BinarySensorEntity):
    """Battery charging power counts as surplus."""

    def __init__(self, controller) -> None:
        super().__init__(controller, "battery_release")

    @property
    def is_on(self) -> bool:
        res = self.controller.result
        return bool(res and res.battery_release)


class SurplusSensor(PvSurplusEntity, BinarySensorEntity):
    """Available power is at or above the switch-on threshold right now."""

    def __init__(self, controller) -> None:
        super().__init__(controller, "surplus")

    @property
    def is_on(self) -> bool:
        res = self.controller.result
        return bool(res and res.surplus_now)


class PeakSensor(PvSurplusEntity, BinarySensorEntity):
    """EVU block (peak mode) requested by the controller (also in observe mode)."""

    def __init__(self, controller) -> None:
        super().__init__(controller, "peak_active")

    @property
    def is_on(self) -> bool:
        return self.controller.state.peak_active


class EvuSignalSensor(PvSurplusEntity, BinarySensorEntity):
    """EVU bit actually set at the heat pump (read back from EMS-ESP)."""

    def __init__(self, controller) -> None:
        super().__init__(controller, "evu_signal_active")

    @property
    def is_on(self) -> bool | None:
        res = self.controller.result
        return res.evu_active if res else None

    @property
    def available(self) -> bool:
        res = self.controller.result
        return res is not None and res.evu_active is not None
