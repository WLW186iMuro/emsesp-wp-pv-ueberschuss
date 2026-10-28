"""Config and options flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    BATTERY_CHARGE_POSITIVE,
    BATTERY_DISCHARGE_POSITIVE,
    CONF_BATTERY_POWER_ENTITY,
    CONF_AVG_PRICE_ENTITY,
    CONF_BACKUP_RESERVE_ENTITY,
    CONF_BATTERY_SIGN,
    CONF_EVU_BIT,
    CONF_EVU_ENTITY,
    CONF_FORECAST_30MIN_ENTITY,
    CONF_FORECAST_REMAINING_ENTITY,
    CONF_GRID_ENTITY,
    CONF_GRID_SIGN,
    CONF_HOURLY_PRICE_ENTITY,
    CONF_HP_POWER_ENTITY,
    CONF_NAME,
    CONF_PRICE_ENTITY,
    CONF_PRICE_UNIT,
    CONF_PVMAXCOMP_ENTITY,
    CONF_SIGNAL_BIT,
    CONF_SIGNAL_ENTITY,
    CONF_SOC_ENTITY,
    DEFAULT_NAME,
    default_name,
    DOMAIN,
    GRID_EXPORT_POSITIVE,
    GRID_IMPORT_POSITIVE,
    PEAK_ENTITIES,
)
from .logic import PRICE_UNIT_AUTO, PRICE_UNIT_MODES, price_unit_factor

OPTIONAL_ENTITIES = [
    CONF_PVMAXCOMP_ENTITY,
    CONF_HP_POWER_ENTITY,
    CONF_FORECAST_REMAINING_ENTITY,
    CONF_FORECAST_30MIN_ENTITY,
    CONF_PRICE_ENTITY,
    *PEAK_ENTITIES,
]
PRICE_ENTITIES = [CONF_PRICE_ENTITY, CONF_HOURLY_PRICE_ENTITY, CONF_AVG_PRICE_ENTITY]


def _entity(domain: str, device_class: str | None = None) -> selector.EntitySelector:
    cfg = selector.EntitySelectorConfig(domain=domain)
    if device_class:
        cfg = selector.EntitySelectorConfig(domain=domain, device_class=device_class)
    return selector.EntitySelector(cfg)


def _schema(include_name: bool, name: str = DEFAULT_NAME) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if include_name:
        fields[vol.Required(CONF_NAME, default=name)] = selector.TextSelector()
    fields.update(
        {
            vol.Required(CONF_SIGNAL_ENTITY): _entity("text"),
            vol.Required(CONF_SIGNAL_BIT, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=14, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_GRID_ENTITY): _entity("sensor", "power"),
            vol.Required(CONF_GRID_SIGN, default=GRID_IMPORT_POSITIVE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[GRID_IMPORT_POSITIVE, GRID_EXPORT_POSITIVE],
                    translation_key="grid_sign",
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_BATTERY_POWER_ENTITY): _entity("sensor", "power"),
            vol.Required(CONF_BATTERY_SIGN, default=BATTERY_DISCHARGE_POSITIVE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[BATTERY_DISCHARGE_POSITIVE, BATTERY_CHARGE_POSITIVE],
                    translation_key="battery_sign",
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_SOC_ENTITY): _entity("sensor", "battery"),
            vol.Optional(CONF_PVMAXCOMP_ENTITY): _entity("number"),
            vol.Optional(CONF_HP_POWER_ENTITY): _entity("sensor", "power"),
            vol.Optional(CONF_FORECAST_REMAINING_ENTITY): _entity("sensor"),
            vol.Optional(CONF_FORECAST_30MIN_ENTITY): _entity("sensor"),
            vol.Optional(CONF_PRICE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Required(CONF_PRICE_UNIT, default=PRICE_UNIT_AUTO): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=PRICE_UNIT_MODES,
                    translation_key="price_unit",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_EVU_ENTITY): _entity("text"),
            vol.Required(CONF_EVU_BIT, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=14, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_BACKUP_RESERVE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "number", "input_number"])
            ),
            vol.Optional(CONF_HOURLY_PRICE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_AVG_PRICE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
        }
    )
    return vol.Schema(fields)


def _validate(hass, user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if user_input.get(CONF_PVMAXCOMP_ENTITY) and not user_input.get(CONF_HP_POWER_ENTITY):
        errors[CONF_HP_POWER_ENTITY] = "hp_power_required"
    # The EVU block (peak mode) needs all of its entities or none
    if any(user_input.get(key) for key in PEAK_ENTITIES):
        for key in PEAK_ENTITIES:
            if not user_input.get(key):
                errors[key] = "peak_incomplete"
    if (user_input.get(CONF_PRICE_UNIT) or PRICE_UNIT_AUTO) == PRICE_UNIT_AUTO:
        for key in PRICE_ENTITIES:
            price_entity = user_input.get(key)
            st = hass.states.get(price_entity) if price_entity else None
            unit = st.attributes.get("unit_of_measurement") if st else None
            # Only complain when the sensor is there and its unit cannot be recognised.
            if (
                st is not None
                and st.state not in ("unknown", "unavailable", "")
                and price_unit_factor(unit) is None
            ):
                errors[CONF_PRICE_UNIT] = "price_unit_unknown"
    return errors


def _normalize(user_input: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_input)
    data[CONF_SIGNAL_BIT] = int(data.get(CONF_SIGNAL_BIT) or 0)
    data[CONF_EVU_BIT] = int(data.get(CONF_EVU_BIT) or 0)
    for key in OPTIONAL_ENTITIES:
        data[key] = data.get(key) or None
    if data.get(CONF_PRICE_UNIT) not in PRICE_UNIT_MODES:
        data[CONF_PRICE_UNIT] = PRICE_UNIT_AUTO
    return data


class PvSurplusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the PV surplus control."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(self.hass, user_input)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_SIGNAL_ENTITY])
                self._abort_if_unique_id_configured()
                data = _normalize(user_input)
                return self.async_create_entry(title=data[CONF_NAME], data=data)
        schema = _schema(include_name=True, name=default_name(self.hass.config.language))
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PvSurplusOptionsFlow()


class PvSurplusOptionsFlow(OptionsFlow):
    """Change the source entities later."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            errors = _validate(self.hass, user_input)
            if not errors:
                data = _normalize(user_input)
                data[CONF_NAME] = current.get(CONF_NAME, DEFAULT_NAME)
                return self.async_create_entry(data=data)
        schema = self.add_suggested_values_to_schema(
            _schema(include_name=False), user_input if user_input is not None else current
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
