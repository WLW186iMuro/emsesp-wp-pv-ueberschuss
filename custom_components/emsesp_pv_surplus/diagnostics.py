"""Diagnostics download (Settings → Devices & services → … → Download diagnostics)."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import VERSION


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    controller = entry.runtime_data
    sources = {}
    for key, entity_id in controller.cfg.items():
        if isinstance(entity_id, str) and "." in entity_id and key.endswith("_entity"):
            st = hass.states.get(entity_id)
            sources[key] = {
                "entity_id": entity_id,
                "state": st.state if st else None,
                "unit": st.attributes.get("unit_of_measurement") if st else None,
            }
    state = controller.state
    return {
        "version": VERSION,
        "config": dict(controller.cfg),
        "settings": controller.settings.to_dict(),
        "state": {
            **state.to_dict(),
            "surplus_since": _plain(state.surplus_since),
            "deficit_since": _plain(state.deficit_since),
            "soc_low_since": _plain(state.soc_low_since),
            "sensor_fail_since": _plain(state.sensor_fail_since),
            "samples": len(state.samples),
            "peak_import_since": _plain(state.peak_import_since),
        },
        "sources": sources,
        "inputs": _plain(controller.inputs),
        "result": _plain(controller.result),
        "last_message": controller.last_message,
    }
