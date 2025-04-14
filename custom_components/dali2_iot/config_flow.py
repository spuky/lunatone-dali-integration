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
from .device import Dali2IotDevice
from .discovery import Dali2IotDiscovery

_LOGGER = logging.getLogger(__name__)

class Dali2IotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DALI2 IoT."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery = None
        self._discovered_devices = {}
        self._host = None
        self._name = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
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
            except Exception as ex:
                _LOGGER.error("Error connecting to device: %s", ex)
                errors["base"] = "cannot_connect"
            else:
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

    async def async_step_discovery(
        self, discovery_info: dict[str, Any]
    ) -> FlowResult:
        """Handle discovery."""
        self._host = discovery_info["host"]
        self._name = discovery_info["name"]

        # Check if we already have this host configured
        await self.async_set_unique_id(self._host)
        self._abort_if_unique_id_configured()

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle discovery confirmation."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_HOST: self._host,
                    CONF_NAME: self._name,
                },
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._name,
                "host": self._host,
            },
        ) 