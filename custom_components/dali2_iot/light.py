"""Light platform for DALI2 IoT integration."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Dali2IotCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DALI2 IoT lights from a config entry."""
    coordinator: Dali2IotCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Get devices from coordinator
    devices = coordinator.data.get("devices", [])
    
    # Create light entities for each device
    entities = []
    for device in devices:
        # Create lights for all DALI devices (they have 'id' and 'features')
        if "id" in device and "features" in device:
            entities.append(Dali2IotLight(coordinator, device))
    
    async_add_entities(entities)

class Dali2IotLight(LightEntity):
    """Representation of a DALI2 IoT light."""

    def __init__(
        self,
        coordinator: Dali2IotCoordinator,
        device: dict[str, Any],
    ) -> None:
        """Initialize the light."""
        self._coordinator = coordinator
        self._device = device
        self._device_id = device["id"]
        self._name = device["name"]
        self._features = device.get("features", {})
        
        # Cache for optimistic updates (immediate UI feedback)
        self._optimistic_state = {}
        self._optimistic_timestamp = 0.0
        
        # Set supported color modes based on device features
        self._attr_supported_color_modes = set()
        if "dimmable" in self._features:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
        if "colorRGB" in self._features:
            self._attr_supported_color_modes.add(ColorMode.RGB)
        if "colorKelvin" in self._features:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
        
        # Set default color mode
        if self._attr_supported_color_modes:
            self._attr_color_mode = next(iter(self._attr_supported_color_modes))
        else:
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the light."""
        return f"dali2_iot_{self._device_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._coordinator.device.device_info

    def _is_optimistic_state_valid(self) -> bool:
        """Check if optimistic state is still valid (within time window)."""
        elapsed = time.time() - self._optimistic_timestamp
        is_valid = elapsed < 5.0  # 5 seconds window
        if self._optimistic_state:
            _LOGGER.debug("Device %s optimistic state: %s, elapsed: %.1fs, valid: %s", 
                         self._device_id, self._optimistic_state, elapsed, is_valid)
        return is_valid

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        # Check optimistic state first for immediate UI feedback
        if "switchable" in self._optimistic_state and self._is_optimistic_state_valid():
            return self._optimistic_state["switchable"]
        
        # Get current device state from coordinator
        current_device = self._coordinator.get_device(self._device_id)
        if current_device and "features" in current_device:
            return current_device["features"].get("switchable", {}).get("status", False)
        return False

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        # Check optimistic state first for immediate UI feedback
        if "brightness" in self._optimistic_state and self._is_optimistic_state_valid():
            return self._optimistic_state["brightness"]
        
        # Get current device state from coordinator
        current_device = self._coordinator.get_device(self._device_id)
        if current_device and "features" in current_device:
            features = current_device["features"]
            if "dimmable" in features:
                dim_value = features["dimmable"].get("status", 0)
                return int(dim_value * 2.55)  # Convert 0-100 to 0-255
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color of the light."""
        # Get current device state from coordinator
        current_device = self._coordinator.get_device(self._device_id)
        if current_device and "features" in current_device:
            features = current_device["features"]
            if "colorRGB" in features:
                color = features["colorRGB"].get("status", {})
                return (
                    int(color.get("r", 0) * 255),
                    int(color.get("g", 0) * 255),
                    int(color.get("b", 0) * 255),
                )
        return None

    @property
    def color_temp(self) -> int | None:
        """Return the color temperature of the light."""
        # Get current device state from coordinator
        current_device = self._coordinator.get_device(self._device_id)
        if current_device and "features" in current_device:
            features = current_device["features"]
            if "colorKelvin" in features:
                return int(features["colorKelvin"].get("status", 4000))
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Optimistically update local state for immediate UI feedback
        self._optimistic_state["switchable"] = True
        self._optimistic_timestamp = time.time()
        
        if ATTR_BRIGHTNESS in kwargs:
            self._optimistic_state["brightness"] = kwargs[ATTR_BRIGHTNESS]
            _LOGGER.debug("Device %s optimistic brightness set to %s", 
                         self._device_id, kwargs[ATTR_BRIGHTNESS])
        
        _LOGGER.debug("Device %s optimistic state set: %s", self._device_id, self._optimistic_state)
        
        # Force immediate UI update with optimistic state
        self.async_write_ha_state()
        
        # Prepare command data
        data = {"switchable": True}
        
        if ATTR_BRIGHTNESS in kwargs:
            data["dimmable"] = kwargs[ATTR_BRIGHTNESS] / 2.55
            
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            data["colorRGB"] = {
                "r": r / 255,
                "g": g / 255,
                "b": b / 255,
            }
            
        if ATTR_COLOR_TEMP in kwargs:
            data["colorKelvin"] = kwargs[ATTR_COLOR_TEMP]
        
        try:
            # Send command to device
            await self._coordinator.device.async_control_device(self._device_id, data)
            
            # Refresh coordinator data but keep optimistic state during grace period
            await self._coordinator.async_request_refresh()
            
        except Exception as err:
            # If command fails, revert optimistic state immediately
            _LOGGER.error("Failed to turn on device %s: %s", self._device_id, err)
            self._optimistic_state.clear()
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # Optimistically update local state for immediate UI feedback
        self._optimistic_state["switchable"] = False
        self._optimistic_timestamp = time.time()
        
        _LOGGER.debug("Device %s optimistic state set: %s", self._device_id, self._optimistic_state)
        
        # Force immediate UI update with optimistic state
        self.async_write_ha_state()
        
        data = {"switchable": False}
        
        try:
            # Send command to device
            await self._coordinator.device.async_control_device(self._device_id, data)
            
            # Refresh coordinator data but keep optimistic state during grace period
            await self._coordinator.async_request_refresh()
            
        except Exception as err:
            # If command fails, revert optimistic state immediately
            _LOGGER.error("Failed to turn off device %s: %s", self._device_id, err)
            self._optimistic_state.clear()
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self._on_coordinator_update)
        )
    
    def _on_coordinator_update(self) -> None:
        """Handle coordinator update - update UI but keep optimistic state if recent."""
        # Only clear optimistic state if it's older than the grace period
        if not self._is_optimistic_state_valid():
            self._optimistic_state.clear()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the light state."""
        await self._coordinator.async_request_refresh() 