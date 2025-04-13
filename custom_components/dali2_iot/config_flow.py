"""Config flow for DALI2 IoT integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_HOST, DOMAIN
from .discovery import Dali2IotDiscovery

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    # TODO: Implement actual validation
    # This is where you would check if you can connect to the device
    pass

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DALI2 IoT."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            # Try to discover devices
            discovery = Dali2IotDiscovery()
            self._discovered_devices = await discovery.discover()

            if self._discovered_devices:
                return await self.async_step_select()

            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step to select discovered device."""
        if user_input is None:
            return self.async_show_form(
                step_id="select",
                data_schema=vol.Schema(
                    {
                        vol.Required("device"): vol.In(
                            {
                                device["host"]: f"{device['name']} ({device['host']})"
                                for device in self._discovered_devices
                            }
                        )
                    }
                ),
            )

        device = next(
            device
            for device in self._discovered_devices
            if device["host"] == user_input["device"]
        )

        # Check if we already have this device configured
        await self.async_set_unique_id(device["host"])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=device["name"],
            data={CONF_HOST: device["host"]},
        ) 