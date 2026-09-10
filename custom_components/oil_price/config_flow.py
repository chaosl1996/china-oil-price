"""Config flow to set up the China Oil Price integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, REGIONS, REGION_NAMES

REGION_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[
            SelectOptionDict(value=slug, label=name) for slug, name in REGIONS
        ],
        mode=SelectSelectorMode.DROPDOWN,
    )
)

SCAN_INTERVAL_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=1,
        max=48,
        step=1,
        unit_of_measurement="小时",
        mode=NumberSelectorMode.BOX,
    )
)


class OilPriceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for China Oil Price."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step: choose a region (and optionally a name)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            region = user_input["region"]
            await self.async_set_unique_id(f"{DOMAIN}-{region}")
            self._abort_if_unique_id_configured()
            name = (user_input.get("name") or "").strip() or f"{REGION_NAMES[region]}油价"
            return self.async_create_entry(title=name, data={"region": region, "name": name})

        schema = vol.Schema(
            {
                vol.Required("region"): REGION_SELECTOR,
                vol.Optional("name"): TextSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow handler."""
        return OilPriceOptionsFlow(config_entry)


class OilPriceOptionsFlow(config_entries.OptionsFlow):
    """Handle options: polling interval."""

    def __init__(self, config_entry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_hours = self._entry.options.get(
            "scan_interval", int(DEFAULT_SCAN_INTERVAL.total_seconds() // 3600)
        )
        schema = vol.Schema(
            {
                vol.Required("scan_interval", default=current_hours): SCAN_INTERVAL_SELECTOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
