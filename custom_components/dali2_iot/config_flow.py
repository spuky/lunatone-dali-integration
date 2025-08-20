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

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return Dali2IotOptionsFlow(config_entry)

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
            
            # Always show the selection form (including manual entry option)
            return await self.async_step_select()

        # This should not be reached as we always go through select step
        return self.async_abort(reason="invalid_flow")

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step to select discovered device or manual entry."""
        if user_input is None:
            # Get already configured hosts
            configured_hosts = {
                entry.data[CONF_HOST] 
                for entry in self._async_current_entries()
            }
            
            # Filter out already configured devices
            available_devices = [
                device for device in self._discovered_devices
                if device["host"] not in configured_hosts
            ]
            
            # Build device selection options
            device_options = {}
            
            # Add available discovered devices
            for device in available_devices:
                device_options[device["host"]] = f"{device['name']} ({device['host']})"
            
            # Add already configured devices (marked as unavailable)
            configured_devices = [
                device for device in self._discovered_devices
                if device["host"] in configured_hosts
            ]
            for device in configured_devices:
                already_configured_text = self.hass.localize("component.dali2_iot.config.device_options.already_configured_suffix") or "Already configured"
                device_options[f"configured_{device['host']}"] = f"{device['name']} ({device['host']}) - {already_configured_text}"
            
            # Always add manual entry option
            manual_entry_text = self.hass.localize("component.dali2_iot.config.device_options.manual_entry") or "Manual entry..."
            device_options["manual"] = manual_entry_text
            
            return self.async_show_form(
                step_id="select",
                data_schema=vol.Schema(
                    {
                        vol.Required("device"): vol.In(device_options)
                    }
                ),
            )

        # Handle user selection
        selected_option = user_input["device"]
        
        # Check if manual entry was selected
        if selected_option == "manual":
            return await self.async_step_manual()
        
        # Check if a configured device was selected (should not be selectable)
        if selected_option.startswith("configured_"):
            return self.async_show_form(
                step_id="select",
                data_schema=vol.Schema(
                    {
                        vol.Required("device"): vol.In(self._get_device_options())
                    }
                ),
                errors={"base": "device_already_configured"},
            )

        # Get selected available device
        selected_device = next(
            device
            for device in self._discovered_devices
            if device["host"] == selected_option
        )

        # Validate the connection
        try:
            test_device = Dali2IotDevice(
                selected_option,
                selected_device["name"],
                async_get_clientsession(self.hass),
            )
            await test_device.async_get_info()
        except Dali2IotConnectionError as ex:
            _LOGGER.error("Error connecting to device at %s: %s", selected_option, ex)
            return self.async_show_form(
                step_id="select",
                data_schema=vol.Schema(
                    {
                        vol.Required("device"): vol.In(self._get_device_options())
                    }
                ),
                errors={"base": "cannot_connect"},
            )

        # Check if we already have this device configured (double-check)
        await self.async_set_unique_id(selected_option)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=selected_device["name"],
            data={
                CONF_HOST: selected_option,
                CONF_NAME: selected_device["name"],
            },
        )
    
    def _get_device_options(self) -> dict[str, str]:
        """Get device options for the selection form."""
        # Get already configured hosts
        configured_hosts = {
            entry.data[CONF_HOST] 
            for entry in self._async_current_entries()
        }
        
        # Filter out already configured devices
        available_devices = [
            device for device in self._discovered_devices
            if device["host"] not in configured_hosts
        ]
        
        # Build device selection options
        device_options = {}
        
        # Add available discovered devices
        for device in available_devices:
            device_options[device["host"]] = f"{device['name']} ({device['host']})"
        
        # Add already configured devices (marked as unavailable)
        configured_devices = [
            device for device in self._discovered_devices
            if device["host"] in configured_hosts
        ]
        for device in configured_devices:
            already_configured_text = self.hass.localize("component.dali2_iot.config.device_options.already_configured_suffix") or "Already configured"
            device_options[f"configured_{device['host']}"] = f"{device['name']} ({device['host']}) - {already_configured_text}"
        
        # Always add manual entry option
        manual_entry_text = self.hass.localize("component.dali2_iot.config.device_options.manual_entry") or "Manual entry..."
        device_options["manual"] = manual_entry_text
        
        return device_options

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual device entry."""
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="manual",
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
                step_id="manual",
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

class Dali2IotOptionsFlow(config_entries.OptionsFlow):
    """Handle DALI2 IoT options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            if user_input.get("scan_devices"):
                return await self.async_step_scan()
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("scan_devices", default=False): bool,
            }),
            description_placeholders={
                "device_host": self.config_entry.data[CONF_HOST],
            },
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the scan step."""
        if user_input is not None:
            # Get the coordinator
            coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if not coordinator:
                return self.async_abort(reason="device_not_found")

            try:
                # Start the scan
                new_installation = user_input.get("new_installation", False)
                _LOGGER.info("Starting DALI scan from options (new_installation=%s)", new_installation)
                scan_result = await coordinator.device.async_start_scan(new_installation)
                _LOGGER.info("DALI scan started: %s", scan_result)
                
                # Refresh coordinator data
                await coordinator.async_request_refresh()
                
                return self.async_create_entry(
                    title="", 
                    data={},
                    description="DALI scan started successfully! New devices will appear automatically in Home Assistant."
                )
                
            except Exception as err:
                _LOGGER.error("Failed to start DALI scan from options: %s", err)
                return self.async_abort(reason="scan_failed")

        return self.async_show_form(
            step_id="scan",
            data_schema=vol.Schema({
                vol.Optional("new_installation", default=False): bool,
            }),
            description_placeholders={
                "device_host": self.config_entry.data[CONF_HOST],
            },
        ) 