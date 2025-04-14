"""Coordinator for DALI2 IoT integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .device import Dali2IotDevice

_LOGGER = logging.getLogger(__name__)

class Dali2IotCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the DALI2 IoT device."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: Dali2IotDevice,
        update_interval: int = 30,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="DALI2 IoT",
            update_interval=update_interval,
        )
        self.device = device
        self._devices: list[dict[str, Any]] = []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the DALI2 IoT device."""
        devices = await self.device.async_get_devices()
        self._devices = devices
        return {"devices": devices}

    def get_device(self, device_id: int) -> dict[str, Any] | None:
        """Get device by ID."""
        for device in self._devices:
            if device.get("id") == device_id:
                return device
        return None 