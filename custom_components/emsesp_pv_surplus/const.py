"""Constants for the EMS-ESP PV surplus integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "emsesp_pv_surplus"
VERSION = "0.3.1"

PLATFORMS = ["binary_sensor", "button", "number", "select", "sensor", "switch", "time"]

CONF_NAME = "name"
CONF_SIGNAL_ENTITY = "signal_entity"
CONF_SIGNAL_BIT = "signal_bit"
CONF_GRID_ENTITY = "grid_entity"
CONF_GRID_SIGN = "grid_sign"
CONF_BATTERY_POWER_ENTITY = "battery_power_entity"
CONF_BATTERY_SIGN = "battery_sign"
CONF_SOC_ENTITY = "soc_entity"
CONF_PVMAXCOMP_ENTITY = "pvmaxcomp_entity"
CONF_HP_POWER_ENTITY = "hp_power_entity"
CONF_FORECAST_REMAINING_ENTITY = "forecast_remaining_entity"
CONF_FORECAST_30MIN_ENTITY = "forecast_30min_entity"
CONF_PRICE_ENTITY = "price_entity"
CONF_PRICE_UNIT = "price_unit"

GRID_IMPORT_POSITIVE = "import_positive"
GRID_EXPORT_POSITIVE = "export_positive"
BATTERY_DISCHARGE_POSITIVE = "discharge_positive"
BATTERY_CHARGE_POSITIVE = "charge_positive"

DEFAULT_NAME = "Heat pump PV surplus"
DEFAULT_NAMES = {"de": "PV-Überschuss Wärmepumpe", "en": DEFAULT_NAME}


def default_name(language: str | None) -> str:
    """Device name suggested in the config flow."""
    return DEFAULT_NAMES.get((language or "en").split("-")[0], DEFAULT_NAME)

TICK_INTERVAL = timedelta(seconds=15)
SIGNAL_REWRITE_INTERVAL = timedelta(seconds=60)
SAVE_DELAY = 10

FRONTEND_URL = f"/{DOMAIN}/emsesp-pv-surplus-card.js"
CARD_FILE = "frontend/emsesp-pv-surplus-card.js"


def signal_update(entry_id: str) -> str:
    """Dispatcher signal sent after every evaluation."""
    return f"{DOMAIN}_{entry_id}_update"
