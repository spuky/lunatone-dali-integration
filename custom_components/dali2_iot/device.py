"""Device class for DALI2 IoT integration."""
from __future__ import annotations

import aiohttp
import asyncio
import async_timeout
import logging
from typing import Any, Final

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

API_TIMEOUT: Final = 10.0
BASE_URL: Final = "http://{host}/api/v1"

class Dali2IotConnectionError(Exception):
    """Error to indicate we cannot connect to the device."""

class Dali2IotDevice:
    """Class to handle a DALI2 IoT device."""

    def __init__(
        self,
        host: str,
        name: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the device."""
        self._host = host
        self._name = name
        self._session = session
        self._base_url = BASE_URL.format(host=host)
        self._device_info: DeviceInfo | None = None
        self._devices: list[dict[str, Any]] = []

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        if not self._device_info:
            self._device_info = DeviceInfo(
                identifiers={("dali2_iot", self._host)},
                name=self._name,
                manufacturer="Lunatone",
                model="DALI2 IoT",
            )
        return self._device_info

    async def async_get_info(self) -> dict[str, Any]:
        """Get device information."""
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._session.get(f"{self._base_url}/info") as response:
                    if response.status == 200:
                        return await response.json()
                    _LOGGER.error("Failed to get device info from %s: %s", self._host, response.status)
                    raise Dali2IotConnectionError(f"Invalid response from device at {self._host}: {response.status}")
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error getting device info from %s: %s", self._host, err)
            raise Dali2IotConnectionError(f"Connection failed to {self._host}: {err}") from err

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Get list of devices from the DALI2 IoT controller."""
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._session.get(f"{self._base_url}/devices") as response:
                    if response.status == 200:
                        data = await response.json()
                        self._devices = data.get("devices", [])
                        return self._devices
                    _LOGGER.error("Failed to get devices from %s: %s", self._host, response.status)
                    raise Dali2IotConnectionError(f"Invalid response from device at {self._host}: {response.status}")
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error getting devices from %s: %s", self._host, err)
            raise Dali2IotConnectionError(f"Connection failed to {self._host}: {err}") from err

    async def async_control_device(
        self, device_id: int, data: dict[str, Any]
    ) -> bool:
        """Control a device."""
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._session.post(
                    f"{self._base_url}/device/{device_id}/control",
                    json=data,
                ) as response:
                    if response.status == 204:
                        return True
                    _LOGGER.error("Failed to control device at %s: %s", self._host, response.status)
                    raise Dali2IotConnectionError(f"Invalid response from device at {self._host}: {response.status}")
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error controlling device at %s: %s", self._host, err)
            raise Dali2IotConnectionError(f"Connection failed to {self._host}: {err}") from err 