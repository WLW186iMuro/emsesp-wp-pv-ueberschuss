"""Fixtures for the Home Assistant integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant

pytest_plugins = "pytest_homeassistant_custom_component"

GRID = "sensor.grid_power"
BATTERY = "sensor.battery_power"
SOC = "sensor.battery_soc"
SIGNAL = "text.boiler_hpin4opt"
PRICE = "sensor.electricity_price"
PRICE_NO_UNIT = "sensor.price_without_unit"
EVU = "text.boiler_hpin1opt"
RESERVE = "sensor.battery_backup_reserve"
HOURLY = "sensor.hourly_price_current"
AVERAGE = "sensor.average_price_today"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components/emsesp_pv_surplus."""
    yield


@pytest.fixture(autouse=True)
def fake_frontend(hass: HomeAssistant):
    """Pretend frontend/http/lovelace are loaded; the card registration is not under test here."""
    hass.config.components.update({"http", "frontend", "lovelace"})
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    with patch("custom_components.emsesp_pv_surplus.add_extra_js_url"):
        yield


@pytest.fixture(autouse=True)
def sun_up():
    with patch("custom_components.emsesp_pv_surplus.controller.is_up", return_value=True) as mock:
        yield mock


@pytest.fixture
def sources(hass: HomeAssistant):
    """Source entities as an inverter / EMS-ESP / tariff integration would provide them."""
    hass.states.async_set(GRID, "-300", {"unit_of_measurement": "W"})
    hass.states.async_set(BATTERY, "0", {"unit_of_measurement": "W"})
    hass.states.async_set(SOC, "90", {"unit_of_measurement": "%"})
    hass.states.async_set(SIGNAL, "000000100000")
    hass.states.async_set(PRICE, "0.2431", {"unit_of_measurement": "EUR/kWh"})
    hass.states.async_set(PRICE_NO_UNIT, "24.31")
    hass.states.async_set(EVU, "000000000001010")
    hass.states.async_set(RESERVE, "20", {"unit_of_measurement": "%"})
    hass.states.async_set(HOURLY, "0.2431", {"unit_of_measurement": "EUR/kWh"})
    hass.states.async_set(AVERAGE, "22.1", {"unit_of_measurement": "ct/kWh"})
