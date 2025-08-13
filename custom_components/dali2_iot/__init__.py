"""The DALI2 IoT integration."""
from __future__ import annotations

import aiohttp
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .device import Dali2IotDevice
from .coordinator import Dali2IotCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DALI2 IoT from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    device = Dali2IotDevice(
        host=entry.data["host"],
        name=entry.data["name"],
        session=session,
    )

    # Create coordinator
    coordinator = Dali2IotCoordinator(hass, device)
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register services
    await _async_setup_services(hass)

    # Forward the setup to the light platform
    await hass.config_entries.async_forward_entry_setups(entry, ["light"])
    return True

async def _async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""
    
    async def async_scan_devices(call) -> None:
        """Service to scan for new DALI devices."""
        device_id = call.data.get("device_id")
        new_installation = call.data.get("new_installation", False)
        
        # Find the coordinator for the specified device
        coordinator = None
        if device_id:
            # Find coordinator by device_id (config entry ID)
            coordinator = hass.data[DOMAIN].get(device_id)
        else:
            # Use the first available coordinator if no device_id specified
            coordinators = list(hass.data[DOMAIN].values())
            if coordinators:
                coordinator = coordinators[0]
        
        if not coordinator:
            _LOGGER.error("No DALI2 IoT device found for scanning")
            return
        
        try:
            _LOGGER.info("Starting DALI device scan (new_installation=%s)", new_installation)
            scan_result = await coordinator.device.async_start_scan(new_installation)
            _LOGGER.info("DALI scan started: %s", scan_result)
            
            # Refresh coordinator data after scan is complete
            await coordinator.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error("Failed to start DALI scan: %s", err)
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        "scan_devices",
        async_scan_devices,
        schema=vol.Schema({
            vol.Optional("device_id"): str,
            vol.Optional("new_installation", default=False): bool,
        })
    )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, ["light"]):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok 