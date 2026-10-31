"""Controller: connects the decision logic with Home Assistant."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.helpers.sun import is_up
from homeassistant.util import dt as dt_util

from .const import (
    BATTERY_CHARGE_POSITIVE,
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_SIGN,
    CONF_FORECAST_30MIN_ENTITY,
    CONF_FORECAST_REMAINING_ENTITY,
    CONF_GRID_ENTITY,
    CONF_GRID_SIGN,
    CONF_HP_POWER_ENTITY,
    CONF_NAME,
    CONF_PRICE_ENTITY,
    CONF_PRICE_UNIT,
    CONF_PVMAXCOMP_ENTITY,
    CONF_SIGNAL_BIT,
    CONF_SIGNAL_ENTITY,
    CONF_SOC_ENTITY,
    DEFAULT_NAME,
    DOMAIN,
    GRID_EXPORT_POSITIVE,
    SAVE_DELAY,
    SIGNAL_REWRITE_INTERVAL,
    TICK_INTERVAL,
    signal_update,
)
from .logic import (
    MODE_OFF,
    PRICE_UNIT_AUTO,
    PRICE_UNIT_MODES,
    RUN_CHEAP,
    Inputs,
    Result,
    Settings,
    State,
    evaluate,
    normalize_price,
    set_bit,
    valid_bits,
)

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1

_TEXT = {
    "de": {
        "observe": "[Beobachtung] ",
        "start": "PV-Betrieb gestartet ({reason})",
        "stop": "PV-Betrieb beendet ({reason})",
        "would_start": "würde PV-Betrieb starten ({reason})",
        "would_stop": "würde PV-Betrieb beenden ({reason})",
        "signal": "Signal {old} → {new}",
        "release": "Betriebsart Aus – Signal auf Normalbetrieb zurückgesetzt ({old} → {new})",
        "comp": "PV max. Kompressorleistung {old} → {new} kW (Budget Ø {budget} W, Kompressor {hp} W, Akku-Freigabe {release})",
        "would_comp": "würde PV max. Kompressorleistung {old} → {new} kW setzen (Budget Ø {budget} W)",
        "comp_cheap": "PV max. Kompressorleistung {old} → {new} kW (günstiger Strom)",
        "would_comp_cheap": "würde PV max. Kompressorleistung {old} → {new} kW setzen (günstiger Strom)",
        "on": "an",
        "off": "aus",
        "reasons": {
            "surplus": "PV-Überschuss",
            "manual": "manuell",
            "mode_off": "Betriebsart Aus",
            "battery_low": "Akku unter Abschaltgrenze",
            "night": "Sonnenuntergang",
            "sensor_error": "Messwerte fehlen",
            "no_surplus": "kein Überschuss mehr",
            "price_cheap": "günstiger Strom",
            "price_end": "günstige Strompreis-Phase vorbei",
            "price_high": "Strompreis zu hoch",
            "hp_idle": "Wärmepumpe fertig, Kompressor steht",
        },
    },
    "en": {
        "observe": "[Observe] ",
        "start": "PV mode started ({reason})",
        "stop": "PV mode ended ({reason})",
        "would_start": "would start PV mode ({reason})",
        "would_stop": "would end PV mode ({reason})",
        "signal": "Signal {old} → {new}",
        "release": "Mode off – signal reset to normal ({old} → {new})",
        "comp": "PV max. compressor power {old} → {new} kW (budget avg {budget} W, compressor {hp} W, battery release {release})",
        "would_comp": "would set PV max. compressor power {old} → {new} kW (budget avg {budget} W)",
        "comp_cheap": "PV max. compressor power {old} → {new} kW (cheap electricity)",
        "would_comp_cheap": "would set PV max. compressor power {old} → {new} kW (cheap electricity)",
        "on": "on",
        "off": "off",
        "reasons": {
            "surplus": "PV surplus",
            "manual": "manual",
            "mode_off": "mode off",
            "battery_low": "battery below stop level",
            "night": "sunset",
            "sensor_error": "readings missing",
            "no_surplus": "surplus gone",
            "price_cheap": "cheap electricity",
            "price_end": "cheap price period over",
            "price_high": "electricity price too high",
            "hp_idle": "heat pump done, compressor idle",
        },
    },
}


class PvSurplusController:
    """Runs the control loop for one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.cfg: dict[str, Any] = {**entry.data, **entry.options}
        self.name: str = self.cfg.get(CONF_NAME) or entry.title or DEFAULT_NAME
        self.bit_index: int = int(self.cfg.get(CONF_SIGNAL_BIT) or 0)
        self.settings = Settings()
        self.state = State()
        self.inputs: Inputs | None = None
        self.result: Result | None = None
        self.last_message: str | None = None
        self.last_message_at: datetime | None = None
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._unsubs: list = []
        self._running = False
        self._prev_mode: str | None = None
        self._last_signal_write: datetime | None = None
        self._last_signal_target: str | None = None
        self._saved_snapshot: dict | None = None
        # ok | unavailable | unit_unknown | None (no price sensor)
        self.price_state: str | None = None
        self.price_raw: float | None = None
        self.price_unit: str | None = None
        lang = (hass.config.language or "en").split("-")[0]
        self._t = _TEXT.get(lang, _TEXT["en"])

    # ------------------------------------------------------------------ setup
    @property
    def has_compressor_control(self) -> bool:
        return bool(self.cfg.get(CONF_PVMAXCOMP_ENTITY)) and bool(self.cfg.get(CONF_HP_POWER_ENTITY))

    @property
    def has_forecast(self) -> bool:
        return bool(self.cfg.get(CONF_FORECAST_REMAINING_ENTITY)) or bool(
            self.cfg.get(CONF_FORECAST_30MIN_ENTITY)
        )

    @property
    def has_price(self) -> bool:
        return bool(self.cfg.get(CONF_PRICE_ENTITY))

    @property
    def price_unit_mode(self) -> str:
        mode = self.cfg.get(CONF_PRICE_UNIT) or PRICE_UNIT_AUTO
        return mode if mode in PRICE_UNIT_MODES else PRICE_UNIT_AUTO

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.settings = Settings.from_dict(data.get("settings"))
        self.state = State.from_dict(data.get("state"))
        self._prev_mode = self.settings.mode
        self._saved_snapshot = self._snapshot()

    async def async_start(self) -> None:
        self._unsubs.append(
            async_track_time_interval(self.hass, self._async_tick, TICK_INTERVAL)
        )

        @callback
        def _started(_hass: HomeAssistant) -> None:
            self.hass.async_create_task(self._async_tick())

        self._unsubs.append(async_at_started(self.hass, _started))

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._store.async_save(self._snapshot())

    # --------------------------------------------------------------- settings
    def update_setting(self, key: str, value: Any) -> None:
        """Called by the settings entities."""
        setattr(self.settings, key, value)
        self._schedule_save(force=True)
        self.hass.async_create_task(self._async_tick())

    def reset_lock(self) -> None:
        self.state.last_off = None
        self._schedule_save(force=True)
        self.hass.async_create_task(self._async_tick())

    def reset_counter(self) -> None:
        self.state.activations = 0
        self._schedule_save(force=True)
        self.hass.async_create_task(self._async_tick())

    def _snapshot(self) -> dict:
        return {"settings": self.settings.to_dict(), "state": self.state.to_dict()}

    def _schedule_save(self, force: bool = False) -> None:
        snap = self._snapshot()
        if force or snap != self._saved_snapshot:
            self._saved_snapshot = snap
            self._store.async_delay_save(self._snapshot, SAVE_DELAY)

    # ----------------------------------------------------------------- inputs
    def _state_obj(self, key: str):
        entity_id = self.cfg.get(key)
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, "", "None"):
            return None
        return st

    def _number(self, key: str) -> tuple[float | None, str | None]:
        st = self._state_obj(key)
        if st is None:
            return None, None
        try:
            return float(st.state), st.attributes.get("unit_of_measurement")
        except (TypeError, ValueError):
            return None, None

    def _power_w(self, key: str) -> float | None:
        value, unit = self._number(key)
        if value is None:
            return None
        factor = {"kW": 1000.0, "MW": 1_000_000.0, "mW": 0.001}.get(unit or "", 1.0)
        return value * factor

    def _energy_kwh(self, key: str) -> float | None:
        value, unit = self._number(key)
        if value is None:
            return None
        factor = {"Wh": 0.001, "MWh": 1000.0}.get(unit or "", 1.0)
        return value * factor

    def _price_ct(self) -> float | None:
        """Current price in cent per kWh; also updates ``price_state`` for the card."""
        if not self.has_price:
            self.price_state = self.price_raw = self.price_unit = None
            return None
        value, unit = self._number(CONF_PRICE_ENTITY)
        self.price_raw, self.price_unit = value, unit
        if value is None:
            self.price_state = "unavailable"
            return None
        price = normalize_price(value, unit, self.price_unit_mode)
        self.price_state = "ok" if price is not None else "unit_unknown"
        return price

    def _read_inputs(self, now: datetime) -> Inputs:
        grid = self._power_w(CONF_GRID_ENTITY)
        if grid is not None and self.cfg.get(CONF_GRID_SIGN) == GRID_EXPORT_POSITIVE:
            grid = -grid
        battery = self._power_w(CONF_BATTERY_POWER_ENTITY)
        if battery is not None and self.cfg.get(CONF_BATTERY_SIGN) == BATTERY_CHARGE_POSITIVE:
            battery = -battery
        soc, _ = self._number(CONF_SOC_ENTITY)
        pvmax, unit = self._number(CONF_PVMAXCOMP_ENTITY)
        if pvmax is not None and unit == "W":
            pvmax = pvmax / 1000.0
        signal = self._state_obj(CONF_SIGNAL_ENTITY)
        try:
            sun_up = is_up(self.hass)
        except Exception:  # noqa: BLE001 - location not configured
            sun_up = True
        return Inputs(
            now=now,
            grid_w=grid,
            battery_w=battery,
            soc=soc,
            sun_up=sun_up,
            forecast_remaining_kwh=self._energy_kwh(CONF_FORECAST_REMAINING_ENTITY),
            forecast_30min_w=self._power_w(CONF_FORECAST_30MIN_ENTITY),
            hp_power_w=self._power_w(CONF_HP_POWER_ENTITY) if self.has_compressor_control else None,
            signal_bits=signal.state if signal else None,
            pvmaxcomp_kw=pvmax if self.has_compressor_control else None,
            price_configured=self.has_price,
            price_ct=self._price_ct(),
        )

    # ------------------------------------------------------------------- loop
    async def _async_tick(self, _now: datetime | None = None) -> None:
        if self._running:
            return
        self._running = True
        try:
            now = dt_util.now()
            inp = self._read_inputs(now)
            res = evaluate(self.settings, self.state, inp, self.bit_index)
            self.inputs = inp
            self.result = res
            await self._async_apply(inp, res, now)
            self._prev_mode = self.settings.mode
            self._schedule_save()
        except Exception:  # noqa: BLE001 - keep the loop alive
            _LOGGER.exception("Evaluation failed")
        finally:
            self._running = False
        async_dispatcher_send(self.hass, signal_update(self.entry.entry_id))

    async def _async_apply(self, inp: Inputs, res: Result, now: datetime) -> None:
        observe = self.settings.observe
        t = self._t
        reason = t["reasons"].get(res.reason or "", res.reason or "")

        if res.started:
            await self._log(t["observe"] + t["would_start"].format(reason=reason) if observe
                            else t["start"].format(reason=reason))
        if res.stopped:
            await self._log(t["observe"] + t["would_stop"].format(reason=reason) if observe
                            else t["stop"].format(reason=reason))

        cheap = res.run_kind == RUN_CHEAP
        if observe:
            if res.write_comp and res.comp_target_kw is not None:
                await self._log(
                    t["observe"]
                    + t["would_comp_cheap" if cheap else "would_comp"].format(
                        old=inp.pvmaxcomp_kw,
                        new=res.comp_target_kw,
                        budget=round(res.budget_avg_w or 0),
                    )
                )
            return

        # Mode switched to off: hand the signal back once
        if (
            self.settings.mode == MODE_OFF
            and self._prev_mode != MODE_OFF
            and res.signal_active
            and valid_bits(inp.signal_bits, self.bit_index)
        ):
            new = set_bit(inp.signal_bits, self.bit_index, False)
            if await self._set_signal(new, now):
                await self._log(t["release"].format(old=inp.signal_bits, new=new))

        # Keep the heat pump signal in line with the decision (also after EMS-ESP restarts)
        if (
            res.enforce_signal
            and res.signal_bits_target is not None
            and res.signal_active is not None
            and res.signal_active != res.desired_signal
        ):
            recently = (
                self._last_signal_write is not None
                and self._last_signal_target == res.signal_bits_target
                and now - self._last_signal_write < SIGNAL_REWRITE_INTERVAL
            )
            if not recently and await self._set_signal(res.signal_bits_target, now):
                await self._log(t["signal"].format(old=inp.signal_bits, new=res.signal_bits_target))

        # Compressor limit
        if res.write_comp and res.comp_target_kw is not None:
            entity_id = self.cfg.get(CONF_PVMAXCOMP_ENTITY)
            try:
                await self.hass.services.async_call(
                    "number",
                    "set_value",
                    {"entity_id": entity_id, "value": res.comp_target_kw},
                    blocking=True,
                )
                await self._log(
                    t["comp_cheap" if cheap else "comp"].format(
                        old=inp.pvmaxcomp_kw,
                        new=res.comp_target_kw,
                        budget=round(res.budget_avg_w or 0),
                        hp=round(inp.hp_power_w or 0),
                        release=t["on"] if res.battery_release else t["off"],
                    )
                )
            except HomeAssistantError as err:
                _LOGGER.warning("Could not set %s: %s", entity_id, err)

    async def _set_signal(self, value: str, now: datetime) -> bool:
        entity_id = self.cfg.get(CONF_SIGNAL_ENTITY)
        self._last_signal_write = now
        self._last_signal_target = value
        try:
            await self.hass.services.async_call(
                "text", "set_value", {"entity_id": entity_id, "value": value}, blocking=True
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Could not write %s to %s: %s", value, entity_id, err)
            return False
        return True

    async def _log(self, message: str) -> None:
        self.last_message = message
        self.last_message_at = dt_util.now()
        _LOGGER.info("%s: %s", self.name, message)
        if not self.hass.services.has_service("logbook", "log"):
            return
        data: dict[str, Any] = {"name": self.name, "message": message}
        status_entity = er.async_get(self.hass).async_get_entity_id(
            "sensor", DOMAIN, f"{self.entry.entry_id}_status"
        )
        if status_entity:
            data["entity_id"] = status_entity
        try:
            await self.hass.services.async_call("logbook", "log", data, blocking=False)
        except HomeAssistantError:
            pass
