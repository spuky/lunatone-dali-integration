"""The DALI2 IoT integration."""
from __future__ import annotations

import aiohttp
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, 
    SERVICE_ADD_TO_GROUP, 
    SERVICE_REMOVE_FROM_GROUP, 
    SERVICE_UPDATE_DEVICE_GROUPS,
    SERVICE_SET_FADE_TIME,
    SERVICE_SET_GROUP_FADE_TIME,
    ATTR_DEVICE_ID,
    ATTR_GROUP_ID,
    ATTR_GROUPS,
    ATTR_FADE_TIME,
)
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
    
    async def async_add_to_group(call) -> None:
        """Service to add a device to a DALI group."""
        device_id = call.data.get(ATTR_DEVICE_ID)
        group_id = call.data.get(ATTR_GROUP_ID)
        entry_id = call.data.get("entry_id")
        
        # Find the coordinator
        coordinator = None
        if entry_id:
            coordinator = hass.data[DOMAIN].get(entry_id)
        else:
            # Use the first available coordinator if no entry_id specified
            coordinators = list(hass.data[DOMAIN].values())
            if coordinators:
                coordinator = coordinators[0]
        
        if not coordinator:
            _LOGGER.error("No DALI2 IoT device found for group management")
            return
        
        try:
            _LOGGER.info("Adding device %s to group %s", device_id, group_id)
            await coordinator.device.async_add_device_to_group(device_id, group_id)
            
            # Refresh coordinator data after group change
            await coordinator.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error("Failed to add device %s to group %s: %s", device_id, group_id, err)

    async def async_remove_from_group(call) -> None:
        """Service to remove a device from a DALI group."""
        device_id = call.data.get(ATTR_DEVICE_ID)
        group_id = call.data.get(ATTR_GROUP_ID)
        entry_id = call.data.get("entry_id")
        
        # Find the coordinator
        coordinator = None
        if entry_id:
            coordinator = hass.data[DOMAIN].get(entry_id)
        else:
            # Use the first available coordinator if no entry_id specified
            coordinators = list(hass.data[DOMAIN].values())
            if coordinators:
                coordinator = coordinators[0]
        
        if not coordinator:
            _LOGGER.error("No DALI2 IoT device found for group management")
            return
        
        try:
            _LOGGER.info("Removing device %s from group %s", device_id, group_id)
            await coordinator.device.async_remove_device_from_group(device_id, group_id)
            
            # Refresh coordinator data after group change
            await coordinator.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error("Failed to remove device %s from group %s: %s", device_id, group_id, err)

    async def async_update_device_groups(call) -> None:
        """Service to update all group memberships for a device."""
        device_id = call.data.get(ATTR_DEVICE_ID)
        groups = call.data.get(ATTR_GROUPS, [])
        entry_id = call.data.get("entry_id")
        
        # Find the coordinator
        coordinator = None
        if entry_id:
            coordinator = hass.data[DOMAIN].get(entry_id)
        else:
            # Use the first available coordinator if no entry_id specified
            coordinators = list(hass.data[DOMAIN].values())
            if coordinators:
                coordinator = coordinators[0]
        
        if not coordinator:
            _LOGGER.error("No DALI2 IoT device found for group management")
            return
        
        try:
            _LOGGER.info("Updating device %s groups to %s", device_id, groups)
            await coordinator.device.async_update_device_groups(device_id, groups)
            
            # Refresh coordinator data after group change
            await coordinator.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error("Failed to update device %s groups: %s", device_id, err)

    async def async_set_fade_time(call) -> None:
        """Service to set fade time for a device."""
        device_id = call.data.get(ATTR_DEVICE_ID)
        fade_time = call.data.get(ATTR_FADE_TIME)
        entry_id = call.data.get("entry_id")
        
        # Find the coordinator
        coordinator = None
        if entry_id:
            coordinator = hass.data[DOMAIN].get(entry_id)
        else:
            # Use the first available coordinator if no entry_id specified
            coordinators = list(hass.data[DOMAIN].values())
            if coordinators:
                coordinator = coordinators[0]
        
        if not coordinator:
            _LOGGER.error("No DALI2 IoT device found for fade time setting")
            return
        
        try:
            _LOGGER.info("Setting fade time for device %s to %s seconds", device_id, fade_time)
            await coordinator.device.async_set_fade_time(device_id, fade_time)
            
        except Exception as err:
            _LOGGER.error("Failed to set fade time for device %s: %s", device_id, err)

    async def async_set_group_fade_time(call) -> None:
        """Service to set fade time for a group."""
        group_id = call.data.get(ATTR_GROUP_ID)
        fade_time = call.data.get(ATTR_FADE_TIME)
        entry_id = call.data.get("entry_id")
        
        # Find the coordinator
        coordinator = None
        if entry_id:
            coordinator = hass.data[DOMAIN].get(entry_id)
        else:
            # Use the first available coordinator if no entry_id specified
            coordinators = list(hass.data[DOMAIN].values())
            if coordinators:
                coordinator = coordinators[0]
        
        if not coordinator:
            _LOGGER.error("No DALI2 IoT device found for group fade time setting")
            return
        
        try:
            _LOGGER.info("Setting fade time for group %s to %s seconds", group_id, fade_time)
            await coordinator.device.async_set_group_fade_time(group_id, fade_time)
            
        except Exception as err:
            _LOGGER.error("Failed to set fade time for group %s: %s", group_id, err)

    # Register the services
    hass.services.async_register(
        DOMAIN,
        "scan_devices",
        async_scan_devices,
        schema=vol.Schema({
            vol.Optional("device_id"): str,
            vol.Optional("new_installation", default=False): bool,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TO_GROUP,
        async_add_to_group,
        schema=vol.Schema({
            vol.Required(ATTR_DEVICE_ID): int,
            vol.Required(ATTR_GROUP_ID): int,
            vol.Optional("entry_id"): str,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_FROM_GROUP,
        async_remove_from_group,
        schema=vol.Schema({
            vol.Required(ATTR_DEVICE_ID): int,
            vol.Required(ATTR_GROUP_ID): int,
            vol.Optional("entry_id"): str,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_DEVICE_GROUPS,
        async_update_device_groups,
        schema=vol.Schema({
            vol.Required(ATTR_DEVICE_ID): int,
            vol.Required(ATTR_GROUPS): [int],
            vol.Optional("entry_id"): str,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FADE_TIME,
        async_set_fade_time,
        schema=vol.Schema({
            vol.Required(ATTR_DEVICE_ID): int,
            vol.Required(ATTR_FADE_TIME): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=60.0)),
            vol.Optional("entry_id"): str,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_GROUP_FADE_TIME,
        async_set_group_fade_time,
        schema=vol.Schema({
            vol.Required(ATTR_GROUP_ID): int,
            vol.Required(ATTR_FADE_TIME): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=60.0)),
            vol.Optional("entry_id"): str,
        })
    )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, ["light"]):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok 