"""Config flow for DALI2 IoT integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .device import Dali2IotDevice, Dali2IotConnectionError
from .discovery import Dali2IotDiscovery

_LOGGER = logging.getLogger(__name__)

class Dali2IotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DALI2 IoT."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery = None
        self._discovered_devices = []
        self._host = None
        self._name = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is None:
            # First time through, try to discover devices
            self._discovery = Dali2IotDiscovery(self.hass)
            self._discovered_devices = await self._discovery.discover()
            
            if self._discovered_devices:
                # If we found devices, show the selection form
                return await self.async_step_select()
            
            # If no devices found, show manual entry form
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_NAME, default="DALI2 IoT"): str,
                    }
                ),
                errors=errors,
            )

        # Handle manual entry
        self._host = user_input[CONF_HOST]
        self._name = user_input[CONF_NAME]

        # Validate the connection
        try:
            device = Dali2IotDevice(
                self._host,
                self._name,
                async_get_clientsession(self.hass),
            )
            await device.async_get_info()
        except Dali2IotConnectionError as ex:
            _LOGGER.error("Error connecting to device at %s: %s", self._host, ex)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_NAME, default="DALI2 IoT"): str,
                    }
                ),
                errors=errors,
            )

        # Check if we already have this host configured
        await self.async_set_unique_id(self._host)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=self._name,
            data={
                CONF_HOST: self._host,
                CONF_NAME: self._name,
            },
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step to select discovered device."""
        if user_input is None:
            # Show selection form
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

        # Get selected device
        selected_host = user_input["device"]
        selected_device = next(
            device
            for device in self._discovered_devices
            if device["host"] == selected_host
        )

        # Check if we already have this device configured
        await self.async_set_unique_id(selected_host)
        self._abort_if_unique_id_configured()

        # Validate the connection
        try:
            test_device = Dali2IotDevice(
                selected_host,
                selected_device["name"],
                async_get_clientsession(self.hass),
            )
            await test_device.async_get_info()
        except Dali2IotConnectionError as ex:
            _LOGGER.error("Error connecting to device at %s: %s", selected_host, ex)
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
                errors={"base": "cannot_connect"},
            )

        return self.async_create_entry(
            title=selected_device["name"],
            data={
                CONF_HOST: selected_host,
                CONF_NAME: selected_device["name"],
            },
        ) 