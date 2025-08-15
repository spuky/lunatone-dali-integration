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
BASE_URL: Final = "http://{host}"

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

    async def async_start_scan(self, new_installation: bool = False) -> dict[str, Any]:
        """Start a DALI device scan."""
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._session.post(
                    f"{self._base_url}/dali/scan",
                    json={"newInstallation": new_installation},
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    _LOGGER.error("Failed to start scan on %s: %s", self._host, response.status)
                    raise Dali2IotConnectionError(f"Failed to start scan on {self._host}: {response.status}")
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error starting scan on %s: %s", self._host, err)
            raise Dali2IotConnectionError(f"Connection failed to {self._host}: {err}") from err

    async def async_get_scan_status(self) -> dict[str, Any]:
        """Get the current scan status."""
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._session.get(f"{self._base_url}/dali/scan") as response:
                    if response.status == 200:
                        return await response.json()
                    _LOGGER.error("Failed to get scan status from %s: %s", self._host, response.status)
                    raise Dali2IotConnectionError(f"Failed to get scan status from {self._host}: {response.status}")
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error getting scan status from %s: %s", self._host, err)
            raise Dali2IotConnectionError(f"Connection failed to {self._host}: {err}") from err

    async def async_update_device_groups(
        self, device_id: int, groups: list[int]
    ) -> bool:
        """Update device group membership."""
        try:
            data = {"groups": groups}
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._session.put(
                    f"{self._base_url}/device/{device_id}",
                    json=data,
                ) as response:
                    if response.status == 200:
                        return True
                    _LOGGER.error("Failed to update device groups at %s: %s", self._host, response.status)
                    raise Dali2IotConnectionError(f"Failed to update device groups at {self._host}: {response.status}")
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error updating device groups at %s: %s", self._host, err)
            raise Dali2IotConnectionError(f"Connection failed to {self._host}: {err}") from err

    async def async_add_device_to_group(
        self, device_id: int, group_id: int
    ) -> bool:
        """Add device to a DALI group."""
        # Get current device data to retrieve existing groups
        devices = await self.async_get_devices()
        device = next((d for d in devices if d["id"] == device_id), None)
        
        if not device:
            _LOGGER.error("Device %s not found", device_id)
            raise Dali2IotConnectionError(f"Device {device_id} not found")
        
        current_groups = device.get("groups", [])
        
        # Add group if not already present
        if group_id not in current_groups:
            new_groups = current_groups + [group_id]
            return await self.async_update_device_groups(device_id, new_groups)
        
        return True  # Already in group

    async def async_remove_device_from_group(
        self, device_id: int, group_id: int
    ) -> bool:
        """Remove device from a DALI group."""
        # Get current device data to retrieve existing groups
        devices = await self.async_get_devices()
        device = next((d for d in devices if d["id"] == device_id), None)
        
        if not device:
            _LOGGER.error("Device %s not found", device_id)
            raise Dali2IotConnectionError(f"Device {device_id} not found")
        
        current_groups = device.get("groups", [])
        
        # Remove group if present
        if group_id in current_groups:
            new_groups = [g for g in current_groups if g != group_id]
            return await self.async_update_device_groups(device_id, new_groups)
        
        return True  # Not in group anyway

    async def async_control_group(
        self, group_id: int, data: dict[str, Any], line: int | None = None
    ) -> bool:
        """Control a DALI group."""
        try:
            url = f"{self._base_url}/group/{group_id}/control"
            params = {}
            if line is not None:
                params["_line"] = line
            
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._session.post(
                    url,
                    json=data,
                    params=params if params else None,
                ) as response:
                    if response.status == 204:
                        return True
                    _LOGGER.error("Failed to control group %s at %s: %s", group_id, self._host, response.status)
                    raise Dali2IotConnectionError(f"Failed to control group {group_id} at {self._host}: {response.status}")
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error controlling group %s at %s: %s", group_id, self._host, err)
            raise Dali2IotConnectionError(f"Connection failed to {self._host}: {err}") from err 