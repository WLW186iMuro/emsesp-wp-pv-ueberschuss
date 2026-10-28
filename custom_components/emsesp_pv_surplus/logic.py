"""Decision logic for the PV surplus controller.

This module deliberately has no Home Assistant imports so it can be unit
tested on its own. The controller in ``controller.py`` reads the source
entities, fills an :class:`Inputs` object, calls :func:`evaluate` and then
carries out what the returned :class:`Result` asks for.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, fields
from datetime import date, datetime, time, timedelta
import re

MODE_AUTO = "auto"
MODE_OFF = "off"
MODE_MANUAL = "manual"
MODES = [MODE_AUTO, MODE_OFF, MODE_MANUAL]

ST_OFF = "off"
ST_MANUAL = "manual"
ST_PV = "pv_active"
ST_DEFICIT = "deficit_pending"
ST_WAIT = "waiting"
ST_PENDING = "surplus_pending"
ST_LOCKED = "locked"
ST_LIMIT = "daily_limit"
ST_WINDOW = "outside_window"
ST_NIGHT = "night"
ST_BATTERY = "battery_low"
ST_SENSOR = "sensor_error"
ST_CHEAP = "price_cheap"
ST_EXPENSIVE = "price_high"
ST_PEAK = "peak_block"
STATUS_OPTIONS = [
    ST_OFF,
    ST_MANUAL,
    ST_PV,
    ST_DEFICIT,
    ST_WAIT,
    ST_PENDING,
    ST_LOCKED,
    ST_LIMIT,
    ST_WINDOW,
    ST_NIGHT,
    ST_BATTERY,
    ST_SENSOR,
    ST_CHEAP,
    ST_EXPENSIVE,
    ST_PEAK,
]

# Reasons used for start/stop events (logbook, last action).
R_AUTO = "surplus"
R_MANUAL = "manual"
R_MODE_OFF = "mode_off"
R_BATTERY = "battery_low"
R_NIGHT = "night"
R_SENSOR = "sensor_error"
R_NO_SURPLUS = "no_surplus"
R_MODE_AUTO = "mode_auto"
R_CHEAP = "price_cheap"
R_PRICE_END = "price_end"
R_PRICE_HIGH = "price_high"
# Reasons for setting / lifting the EVU block (peak mode)
R_PEAK = "peak"
R_PEAK_END = "peak_end"
R_PEAK_MAX = "peak_max"
R_PEAK_OFF = "peak_disabled"

# Why the heat pump is currently in PV mode
RUN_PV = "pv"
RUN_CHEAP = "cheap"
RUN_MANUAL = "manual"
RUN_KINDS = [RUN_PV, RUN_CHEAP, RUN_MANUAL]

# How the unit of the price sensor is interpreted
PRICE_UNIT_AUTO = "auto"
PRICE_UNIT_MAJOR_KWH = "major_kwh"  # e.g. EUR/kWh
PRICE_UNIT_MINOR_KWH = "minor_kwh"  # e.g. ct/kWh
PRICE_UNIT_MAJOR_MWH = "major_mwh"  # e.g. EUR/MWh
PRICE_UNIT_MODES = [PRICE_UNIT_AUTO, PRICE_UNIT_MAJOR_KWH, PRICE_UNIT_MINOR_KWH, PRICE_UNIT_MAJOR_MWH]

CHECK_KEYS = [
    "sensors",
    "sun",
    "window",
    "battery",
    "lock",
    "limit",
    "surplus",
    "forecast",
    "price",
    "delay",
]

# Conditions for the EVU block (peak mode), in display order
PEAK_CHECK_KEYS = [
    "sensors",
    "pv_off",
    "expensive",
    "above_average",
    "battery",
    "lock",
    "limit",
    "no_surplus",
]
# Default position of the EVU block: first character of the input option (1xxxxxxxxxxxxxx).
EVU_BIT = 0

SOC_STOP_DELAY = timedelta(minutes=2)
SENSOR_FAIL_DELAY = timedelta(minutes=10)
# Short dropouts (EMS-ESP/MQTT reconnects, inverter polling gaps) are common.
# Keep the previous status for this long before reporting a sensor error.
SENSOR_STATUS_GRACE = timedelta(minutes=2)
MAX_RUNTIME_GAP_S = 120.0
# Price sensors often go unavailable for a moment at the hour/quarter change.
PRICE_GRACE = timedelta(minutes=15)
_BITS = re.compile(r"^[01]+$")


def _fmt_time(value: time) -> str:
    return value.strftime("%H:%M:%S")


def _parse_time(value: str | time) -> time:
    if isinstance(value, time):
        return value
    parts = [int(p) for p in str(value).split(":")]
    while len(parts) < 3:
        parts.append(0)
    return time(parts[0], parts[1], parts[2])


@dataclass
class Settings:
    """User adjustable settings (exposed as entities)."""

    mode: str = MODE_AUTO
    observe: bool = True
    dynamic_power: bool = True
    use_forecast: bool = True
    on_threshold_w: float = 1500.0
    off_threshold_w: float = -800.0
    on_delay_min: float = 5.0
    off_delay_min: float = 10.0
    soc_release: float = 80.0
    soc_forecast: float = 60.0
    soc_stop: float = 50.0
    battery_capacity_kwh: float = 10.0
    forecast_reserve_kwh: float = 4.0
    min_runtime_min: float = 30.0
    lock_min: float = 120.0
    max_activations: float = 2.0
    window_start: time = time(10, 0)
    window_end: time = time(16, 0)
    comp_min_kw: float = 1.0
    comp_max_kw: float = 2.5
    comp_reserve_kw: float = 0.1
    comp_step_kw: float = 0.2
    comp_interval_min: float = 5.0
    price_control: bool = False
    price_cheap_ct: float = 15.0
    price_expensive_ct: float = 35.0
    price_stop_expensive: bool = False
    price_comp_kw: float = 2.5
    peak_factor_pct: float = 108.0
    peak_soc_margin: float = 2.0
    peak_lock_min: float = 60.0
    peak_max_per_day: float = 2.0
    peak_import_min: float = 10.0
    peak_max_duration_min: float = 120.0

    def to_dict(self) -> dict:
        out = {}
        for f in fields(self):
            value = getattr(self, f.name)
            out[f.name] = _fmt_time(value) if isinstance(value, time) else value
        return out

    @classmethod
    def from_dict(cls, data: dict | None) -> Settings:
        settings = cls()
        if not data:
            return settings
        for f in fields(cls):
            if f.name not in data:
                continue
            value = data[f.name]
            default = getattr(settings, f.name)
            try:
                if isinstance(default, time):
                    value = _parse_time(value)
                elif isinstance(default, bool):
                    value = bool(value)
                elif isinstance(default, float):
                    value = float(value)
                elif isinstance(default, str):
                    value = str(value)
            except (TypeError, ValueError):
                continue
            setattr(settings, f.name, value)
        if settings.mode not in MODES:
            settings.mode = MODE_AUTO
        return settings


@dataclass
class Inputs:
    """Snapshot of the source entities at one evaluation."""

    now: datetime
    grid_w: float | None  # + import / - export
    battery_w: float | None  # + discharge / - charge
    soc: float | None
    sun_up: bool = True
    forecast_remaining_kwh: float | None = None
    forecast_30min_w: float | None = None
    hp_power_w: float | None = None
    signal_bits: str | None = None
    pvmaxcomp_kw: float | None = None
    price_configured: bool = False  # a price sensor is set up
    price_ct: float | None = None  # current price in cent (1/100 currency) per kWh
    peak_configured: bool = False  # EVU input, reserve and both peak prices are set up
    peak_price_ct: float | None = None  # hourly price, cent per kWh
    avg_price_ct: float | None = None  # average price today, cent per kWh
    backup_reserve: float | None = None  # battery backup reserve in %
    evu_bits: str | None = None  # input option used for the EVU block


_MAJOR = {
    "eur", "€", "euro", "euros", "nok", "sek", "dkk", "gbp", "£", "chf", "usd", "$", "pln", "czk",
}
_MINOR = {
    "c", "ct", "cent", "cents", "eurocent", "øre", "öre", "ore", "p", "pence", "rp", "rappen", "gr", "grosz",
}
_ENERGY = {"kwh": 1.0, "mwh": 0.001, "wh": 1000.0}


def price_unit_factor(unit: str | None) -> float | None:
    """Factor that converts a price in ``unit`` to cent per kWh. None if unknown."""
    if not unit:
        return None
    text = str(unit).strip().lower().replace(" ", "").replace(".", "")
    if text.count("/") != 1:
        return None
    money, energy = text.split("/")
    if energy not in _ENERGY:
        return None
    if money in _MAJOR:
        base = 100.0
    elif money in _MINOR:
        base = 1.0
    else:
        return None
    return base * _ENERGY[energy]


def normalize_price(value: float | None, unit: str | None, mode: str = PRICE_UNIT_AUTO) -> float | None:
    """Price in cent per kWh, or None if the value or the unit cannot be used."""
    if value is None:
        return None
    if mode == PRICE_UNIT_MAJOR_KWH:
        factor = 100.0
    elif mode == PRICE_UNIT_MINOR_KWH:
        factor = 1.0
    elif mode == PRICE_UNIT_MAJOR_MWH:
        factor = 0.1
    else:
        factor = price_unit_factor(unit)
    if factor is None:
        return None
    return float(value) * factor


def _dt_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _str_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class State:
    """Runtime state. The first block is persisted, the rest is volatile."""

    requested: bool = False
    requested_since: datetime | None = None
    last_off: datetime | None = None
    day: date | None = None
    activations: int = 0
    runtime_s: float = 0.0
    last_adjust: datetime | None = None
    last_action: str | None = None
    last_action_at: datetime | None = None
    run_kind: str = RUN_PV
    peak_active: bool = False
    peak_since: datetime | None = None
    peak_last_end: datetime | None = None
    peak_count: int = 0
    evu_written: bool = False  # EVU bit was (to be) set by us and is not confirmed back at 0

    surplus_since: datetime | None = None
    deficit_since: datetime | None = None
    soc_low_since: datetime | None = None
    sensor_fail_since: datetime | None = None
    last_eval: datetime | None = None
    last_status: str | None = None
    last_price: float | None = None
    last_price_at: datetime | None = None
    samples: deque = field(default_factory=deque)
    peak_import_since: datetime | None = None
    held: dict = field(default_factory=dict)  # last good price values: key -> (time, value)

    def to_dict(self) -> dict:
        return {
            "requested": self.requested,
            "requested_since": _dt_to_str(self.requested_since),
            "last_off": _dt_to_str(self.last_off),
            "day": self.day.isoformat() if self.day else None,
            "activations": self.activations,
            "runtime_s": round(self.runtime_s, 1),
            "last_action": self.last_action,
            "last_action_at": _dt_to_str(self.last_action_at),
            "run_kind": self.run_kind,
            "peak_active": self.peak_active,
            "peak_since": _dt_to_str(self.peak_since),
            "peak_last_end": _dt_to_str(self.peak_last_end),
            "peak_count": self.peak_count,
            "evu_written": self.evu_written,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> State:
        state = cls()
        if not data:
            return state
        state.requested = bool(data.get("requested", False))
        state.requested_since = _str_to_dt(data.get("requested_since"))
        state.last_off = _str_to_dt(data.get("last_off"))
        day = data.get("day")
        try:
            state.day = date.fromisoformat(day) if day else None
        except ValueError:
            state.day = None
        state.activations = int(data.get("activations", 0) or 0)
        state.runtime_s = float(data.get("runtime_s", 0.0) or 0.0)
        state.last_action = data.get("last_action")
        state.last_action_at = _str_to_dt(data.get("last_action_at"))
        kind = data.get("run_kind")
        state.run_kind = kind if kind in RUN_KINDS else RUN_PV
        if state.requested and state.requested_since is None:
            state.requested = False
        state.peak_active = bool(data.get("peak_active", False))
        state.peak_since = _str_to_dt(data.get("peak_since"))
        state.peak_last_end = _str_to_dt(data.get("peak_last_end"))
        state.peak_count = int(data.get("peak_count", 0) or 0)
        state.evu_written = bool(data.get("evu_written", False))
        if state.peak_active and state.peak_since is None:
            state.peak_active = False
        return state


@dataclass
class Result:
    """Outcome of one evaluation."""

    status: str
    checks: dict[str, bool]
    available_w: float | None = None
    budget_w: float | None = None
    budget_avg_w: float | None = None
    battery_release: bool = False
    battery_missing_kwh: float | None = None
    surplus_now: bool = False
    desired_signal: bool = False
    enforce_signal: bool = False
    signal_active: bool | None = None
    signal_bits_target: str | None = None
    comp_target_kw: float | None = None
    comp_due: bool = False
    write_comp: bool = False
    started: bool = False
    stopped: bool = False
    reason: str | None = None
    lock_until: datetime | None = None
    min_runtime_until: datetime | None = None
    surplus_since: datetime | None = None
    deficit_since: datetime | None = None
    runtime_today_s: float = 0.0
    run_kind: str | None = None
    price_active: bool = False
    price_ct: float | None = None
    price_cheap: bool = False
    price_expensive: bool = False
    peak_active: bool = False
    peak_checks: dict[str, bool] = field(default_factory=dict)
    peak_started: bool = False
    peak_stopped: bool = False
    peak_reason: str | None = None
    peak_price_ct: float | None = None
    avg_price_ct: float | None = None
    peak_limit_ct: float | None = None
    peak_since: datetime | None = None
    peak_until: datetime | None = None  # end of the maximum block duration
    peak_lock_until: datetime | None = None
    peak_import_since: datetime | None = None
    evu_active: bool | None = None
    evu_desired: bool = False
    evu_enforce: bool = False
    evu_bits_target: str | None = None


def battery_missing_kwh(soc: float | None, capacity_kwh: float) -> float | None:
    """Energy still needed to fill the battery."""
    if soc is None:
        return None
    return max(0.0, (100.0 - soc) / 100.0 * capacity_kwh)


def battery_release(settings: Settings, soc: float | None, remaining_kwh: float | None) -> bool:
    """True when battery charging power may count as surplus."""
    if soc is None:
        return False
    if soc >= settings.soc_release:
        return True
    if not settings.use_forecast or remaining_kwh is None:
        return False
    missing = battery_missing_kwh(soc, settings.battery_capacity_kwh) or 0.0
    return soc >= settings.soc_forecast and remaining_kwh - settings.forecast_reserve_kwh >= missing


def available_power(grid_w: float, battery_w: float, release: bool) -> float:
    """Power left for the heat pump.

    Grid export counts as surplus. Battery discharge is always subtracted.
    Battery charging counts as surplus only when ``release`` is True.
    """
    battery_part = battery_w if release else max(battery_w, 0.0)
    return -grid_w - battery_part


def compressor_target(settings: Settings, budget_avg_w: float | None, release: bool) -> float:
    """Compressor limit in kW for the averaged power budget."""
    lo = min(settings.comp_min_kw, settings.comp_max_kw)
    hi = max(settings.comp_min_kw, settings.comp_max_kw)
    if not release or budget_avg_w is None:
        return round(lo, 1)
    raw = round(budget_avg_w / 1000.0 - settings.comp_reserve_kw, 1)
    return round(min(hi, max(lo, raw)), 1)


def in_window(now_t: time, start: time, end: time) -> bool:
    if start == end:
        return True
    if start < end:
        return start <= now_t < end
    return now_t >= start or now_t < end


def set_bit(bits: str, index: int, on: bool) -> str:
    return bits[:index] + ("1" if on else "0") + bits[index + 1 :]


def valid_bits(bits: str | None, index: int) -> bool:
    return bool(bits) and bool(_BITS.match(bits)) and 0 <= index < len(bits)


def _held(state: State, key: str, value: float | None, now: datetime) -> float | None:
    """Value, or the last good one for up to PRICE_GRACE (price sensors drop out at the hour)."""
    if value is not None:
        state.held[key] = (now, value)
        return value
    last = state.held.get(key)
    if last is not None and now - last[0] <= PRICE_GRACE:
        return last[1]
    return None


def evaluate(
    settings: Settings, state: State, inp: Inputs, bit_index: int = 0, evu_bit: int = EVU_BIT
) -> Result:
    """Run one control step. Mutates ``state``."""
    now = inp.now

    # Runtime bookkeeping and day rollover
    delta = 0.0
    if state.last_eval is not None:
        delta = min(max((now - state.last_eval).total_seconds(), 0.0), MAX_RUNTIME_GAP_S)
    today = now.date()
    if state.day != today:
        state.day = today
        state.activations = 0
        state.runtime_s = 0.0
        state.peak_count = 0
    if state.requested:
        state.runtime_s += delta

    sensors_ok = inp.grid_w is not None and inp.battery_w is not None and inp.soc is not None
    if sensors_ok:
        state.sensor_fail_since = None
    elif state.sensor_fail_since is None:
        state.sensor_fail_since = now

    release = battery_release(settings, inp.soc, inp.forecast_remaining_kwh)
    missing = battery_missing_kwh(inp.soc, settings.battery_capacity_kwh)

    available = None
    budget = None
    if sensors_ok:
        available = available_power(inp.grid_w, inp.battery_w, release)
        if inp.hp_power_w is not None:
            budget = available + inp.hp_power_w

    window = timedelta(minutes=max(settings.comp_interval_min, 1.0))
    if budget is not None:
        state.samples.append((now, budget))
    while state.samples and now - state.samples[0][0] > window:
        state.samples.popleft()
    budget_avg = (
        sum(v for _, v in state.samples) / len(state.samples) if state.samples else None
    )

    forecast_ok = (
        not settings.use_forecast
        or inp.forecast_30min_w is None
        or inp.forecast_30min_w >= settings.on_threshold_w
    )
    surplus_now = available is not None and available >= settings.on_threshold_w
    raw_on = surplus_now and forecast_ok
    raw_off = available is not None and available <= settings.off_threshold_w

    if raw_on:
        state.surplus_since = state.surplus_since or now
    else:
        state.surplus_since = None
    if raw_off:
        state.deficit_since = state.deficit_since or now
    else:
        state.deficit_since = None

    soc_low = inp.soc is not None and inp.soc < settings.soc_stop
    if soc_low:
        state.soc_low_since = state.soc_low_since or now
    else:
        state.soc_low_since = None

    # Electricity price (optional, only with a price sensor and the switch on)
    price_active = settings.price_control and inp.price_configured
    if inp.price_ct is not None:
        state.last_price = inp.price_ct
        state.last_price_at = now
    price = None
    if price_active:
        if inp.price_ct is not None:
            price = inp.price_ct
        elif state.last_price_at is not None and now - state.last_price_at <= PRICE_GRACE:
            price = state.last_price
    cheap_now = price is not None and price <= settings.price_cheap_ct
    expensive_now = price is not None and not cheap_now and price >= settings.price_expensive_ct

    lock_until = (
        state.last_off + timedelta(minutes=settings.lock_min) if state.last_off else None
    )
    lock_ok = lock_until is None or now >= lock_until
    limit_ok = state.activations < int(settings.max_activations)
    window_ok = in_window(now.time(), settings.window_start, settings.window_end)
    delay_ok = state.surplus_since is not None and (
        now - state.surplus_since >= timedelta(minutes=settings.on_delay_min)
    )
    checks = {
        "sensors": sensors_ok,
        "sun": inp.sun_up,
        "window": window_ok,
        "battery": inp.soc is not None and inp.soc > settings.soc_stop,
        "lock": lock_ok,
        "limit": limit_ok,
        "surplus": surplus_now,
        "forecast": forecast_ok,
        "delay": delay_ok,
    }
    if price_active:
        checks["price"] = not expensive_now

    result = Result(status=ST_WAIT, checks=checks)

    # EVU block (peak mode): block the heat pump while the price is high and the battery is empty
    # Price control is a precondition, not a check: the card hides the EVU block while it is off
    peak_enabled = inp.peak_configured and settings.price_control and settings.mode == MODE_AUTO
    peak_price = _held(state, "peak", inp.peak_price_ct, now) if inp.peak_configured else None
    avg_price = _held(state, "avg", inp.avg_price_ct, now) if inp.peak_configured else None
    peak_limit = avg_price * settings.peak_factor_pct / 100.0 if avg_price is not None else None
    if available is not None and available <= 0:
        state.peak_import_since = state.peak_import_since or now
    elif sensors_ok:
        state.peak_import_since = None
    peak_lock_until = (
        state.peak_last_end + timedelta(minutes=settings.peak_lock_min) if state.peak_last_end else None
    )
    evu_ok = valid_bits(inp.evu_bits, evu_bit)
    peak_checks: dict[str, bool] = {}
    if inp.peak_configured:
        peak_checks = {
            "sensors": sensors_ok and evu_ok,  # grid, battery, SoC and the EVU input
            "pv_off": settings.mode == MODE_AUTO and not state.requested,
            "expensive": peak_price is not None and peak_price >= settings.price_expensive_ct,
            "above_average": peak_price is not None and peak_limit is not None and peak_price > peak_limit,
            "battery": (
                inp.soc is not None
                and inp.backup_reserve is not None
                and inp.soc <= inp.backup_reserve + settings.peak_soc_margin
            ),
            "lock": peak_lock_until is None or now >= peak_lock_until,
            "limit": state.peak_count < int(settings.peak_max_per_day),
            "no_surplus": sensors_ok
            and state.peak_import_since is not None
            and now - state.peak_import_since >= timedelta(minutes=settings.peak_import_min),
        }

    def peak_release(reason: str) -> None:
        state.peak_active = False
        state.peak_since = None
        state.peak_last_end = now
        result.peak_stopped = True
        result.peak_reason = reason

    if state.peak_active:
        since = state.peak_since or now
        if not peak_enabled:
            peak_release(R_MODE_OFF if settings.mode == MODE_OFF else R_PEAK_OFF)
        elif state.sensor_fail_since and now - state.sensor_fail_since >= SENSOR_FAIL_DELAY:
            peak_release(R_SENSOR)
        elif now - since >= timedelta(minutes=settings.peak_max_duration_min):
            peak_release(R_PEAK_MAX)  # whatever the price is
        elif not (peak_price is not None and peak_limit is not None and peak_price >= peak_limit):
            peak_release(R_PEAK_END)
    elif peak_enabled and peak_checks and all(peak_checks.values()):
        state.peak_active = True
        state.peak_since = now
        state.peak_count += 1
        result.peak_started = True
        result.peak_reason = R_PEAK
    if state.peak_active and not settings.observe:
        state.evu_written = True

    def start(reason: str, count: bool, kind: str) -> None:
        state.requested = True
        state.run_kind = kind
        state.requested_since = now
        state.last_adjust = None
        if count:
            state.activations += 1
        state.last_action = f"start:{reason}"
        state.last_action_at = now
        result.started = True
        result.reason = reason

    def stop(reason: str) -> None:
        state.requested = False
        state.requested_since = None
        state.last_off = now
        state.deficit_since = None
        state.last_action = f"stop:{reason}"
        state.last_action_at = now
        result.stopped = True
        result.reason = reason

    if settings.mode == MODE_OFF:
        if state.requested:
            stop(R_MODE_OFF)
    elif settings.mode == MODE_MANUAL:
        if not state.requested:
            start(R_MANUAL, count=False, kind=RUN_MANUAL)
    elif state.requested:
        since = state.requested_since or now
        min_runtime_done = now - since >= timedelta(minutes=settings.min_runtime_min)
        if state.run_kind == RUN_CHEAP:
            # Running on cheap grid power: battery level, sun and start window do not matter.
            if cheap_now:
                pass
            elif surplus_now and inp.sun_up and not soc_low:
                state.run_kind = RUN_PV  # cheap phase over, but PV surplus carries on
                state.deficit_since = None
            elif min_runtime_done:
                stop(R_PRICE_END)
        else:
            if state.run_kind != RUN_PV:
                state.run_kind = RUN_PV  # e.g. back from manual mode
            if cheap_now:
                state.run_kind = RUN_CHEAP  # keep running on cheap grid power (e.g. at sunset)
            elif state.soc_low_since and now - state.soc_low_since >= SOC_STOP_DELAY:
                stop(R_BATTERY)
            elif not inp.sun_up:
                stop(R_NIGHT)
            elif state.sensor_fail_since and now - state.sensor_fail_since >= SENSOR_FAIL_DELAY:
                stop(R_SENSOR)
            elif (
                min_runtime_done
                and state.deficit_since is not None
                and now - state.deficit_since >= timedelta(minutes=settings.off_delay_min)
            ):
                stop(R_NO_SURPLUS)
            elif expensive_now and settings.price_stop_expensive and min_runtime_done:
                stop(R_PRICE_HIGH)
    elif state.peak_active:
        pass  # heat pump is blocked, no PV mode
    elif cheap_now and lock_ok:
        start(R_CHEAP, count=False, kind=RUN_CHEAP)
    elif all(checks.values()):
        start(R_AUTO, count=True, kind=RUN_PV)

    # Recompute lock after a stop in this step
    if result.stopped:
        lock_until = now + timedelta(minutes=settings.lock_min)

    # Status
    if settings.mode == MODE_OFF:
        status = ST_OFF
    elif state.peak_active:
        status = ST_PEAK
    elif state.requested:
        if settings.mode == MODE_MANUAL:
            status = ST_MANUAL
        elif state.run_kind == RUN_CHEAP:
            status = ST_CHEAP
        elif state.deficit_since is not None:
            status = ST_DEFICIT
        else:
            status = ST_PV
    elif not sensors_ok:
        if (
            state.last_status is not None
            and state.last_status != ST_SENSOR
            and state.sensor_fail_since is not None
            and now - state.sensor_fail_since < SENSOR_STATUS_GRACE
        ):
            status = state.last_status
        else:
            status = ST_SENSOR
    elif not inp.sun_up:
        status = ST_NIGHT
    elif not limit_ok:
        status = ST_LIMIT
    elif lock_until is not None and now < lock_until:
        status = ST_LOCKED
    elif not checks["battery"]:
        status = ST_BATTERY
    elif expensive_now:
        status = ST_EXPENSIVE
    elif not window_ok:
        status = ST_WINDOW
    elif raw_on:
        status = ST_PENDING
    else:
        status = ST_WAIT
    result.status = status
    state.last_status = status

    # Signal for the heat pump
    result.desired_signal = state.requested and settings.mode != MODE_OFF
    result.enforce_signal = settings.mode != MODE_OFF
    if valid_bits(inp.signal_bits, bit_index):
        result.signal_active = inp.signal_bits[bit_index] == "1"
        result.signal_bits_target = set_bit(inp.signal_bits, bit_index, result.desired_signal)

    # EVU input: set while blocked; reset only what we set ourselves
    result.evu_desired = state.peak_active
    result.evu_enforce = state.peak_active or state.evu_written
    if evu_ok:
        result.evu_active = inp.evu_bits[evu_bit] == "1"
        result.evu_bits_target = set_bit(inp.evu_bits, evu_bit, result.evu_desired)
        if not state.peak_active and not result.evu_active:
            state.evu_written = False
            result.evu_enforce = False

    # Compressor limit
    cheap_run = state.requested and state.run_kind == RUN_CHEAP and settings.mode == MODE_AUTO
    if cheap_run and settings.dynamic_power and inp.pvmaxcomp_kw is not None:
        # Fixed limit while running on cheap grid power
        target = round(settings.price_comp_kw, 1)
        result.comp_target_kw = target
        due = state.last_adjust is None or now - state.last_adjust >= timedelta(
            minutes=max(settings.comp_interval_min, 1.0)
        )
        if due:
            state.last_adjust = now
            result.comp_due = True
            result.write_comp = abs(target - inp.pvmaxcomp_kw) >= 0.05
    elif (
        settings.dynamic_power
        and state.requested
        and inp.pvmaxcomp_kw is not None
        and budget_avg is not None
    ):
        due = state.last_adjust is None or now - state.last_adjust >= timedelta(
            minutes=max(settings.comp_interval_min, 1.0)
        )
        target = compressor_target(settings, budget_avg, release)
        result.comp_target_kw = target
        if due:
            state.last_adjust = now
            result.comp_due = True
            lo = min(settings.comp_min_kw, settings.comp_max_kw)
            hi = max(settings.comp_min_kw, settings.comp_max_kw)
            current = inp.pvmaxcomp_kw
            result.write_comp = (
                abs(target - current) >= settings.comp_step_kw - 1e-9
                or current < lo - 1e-9
                or current > hi + 1e-9
            )

    result.available_w = available
    result.budget_w = budget
    result.budget_avg_w = budget_avg
    result.battery_release = release
    result.battery_missing_kwh = missing
    result.surplus_now = surplus_now
    result.lock_until = lock_until if lock_until and now < lock_until else None
    if state.requested and state.requested_since:
        until = state.requested_since + timedelta(minutes=settings.min_runtime_min)
        result.min_runtime_until = until if now < until else None
    result.surplus_since = state.surplus_since
    result.deficit_since = state.deficit_since
    result.runtime_today_s = state.runtime_s
    result.run_kind = state.run_kind if state.requested else None
    result.price_active = price_active
    result.price_ct = price
    result.price_cheap = cheap_now
    result.price_expensive = expensive_now
    result.peak_active = state.peak_active
    result.peak_checks = peak_checks
    result.peak_price_ct = peak_price
    result.avg_price_ct = avg_price
    result.peak_limit_ct = peak_limit
    result.peak_since = state.peak_since
    if state.peak_active and state.peak_since:
        until = state.peak_since + timedelta(minutes=settings.peak_max_duration_min)
        result.peak_until = until if now < until else None
    if result.peak_stopped:
        peak_lock_until = now + timedelta(minutes=settings.peak_lock_min)
    result.peak_lock_until = peak_lock_until if peak_lock_until and now < peak_lock_until else None
    result.peak_import_since = state.peak_import_since

    state.last_eval = now
    return result
