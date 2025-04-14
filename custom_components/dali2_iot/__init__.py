"""The DALI2 IoT integration."""
from __future__ import annotations

import aiohttp
import logging
from typing import Any

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

    # Forward the setup to the light platform
    await hass.config_entries.async_forward_entry_setups(entry, ["light"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, ["light"]):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok 