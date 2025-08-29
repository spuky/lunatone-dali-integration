"""Light platform for DALI2 IoT integration."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    DEFAULT_MIN_KELVIN,
    DEFAULT_MAX_KELVIN,
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
    
    # Get devices and groups from coordinator
    devices = coordinator.data.get("devices", [])
    groups = coordinator.data.get("groups", {})
    
    # Create light entities
    entities = []
    
    # Create lights for individual DALI devices
    for device in devices:
        if "id" in device and "features" in device:
            entities.append(Dali2IotLight(coordinator, device))
    
    # Create lights for DALI groups
    for group_id, group_data in groups.items():
        if group_data.get("members"):  # Only create groups with members
            entities.append(Dali2IotGroupLight(coordinator, group_data))
    
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
        self._groups = device.get("groups", [])
        
        # Cache for optimistic updates (immediate UI feedback)
        self._optimistic_state = {}
        self._optimistic_timestamp = 0.0
        
        # Set supported color modes based on device features
        # Home Assistant requires specific combinations - can't mix certain modes
        self._attr_supported_color_modes = set()
        
        # Priority order: RGB > COLOR_TEMP > BRIGHTNESS > ONOFF
        if "colorRGB" in self._features:
            self._attr_supported_color_modes.add(ColorMode.RGB)
            self._attr_color_mode = ColorMode.RGB
        elif "colorKelvin" in self._features:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.COLOR_TEMP
            # Set kelvin temperature range
            self._attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN  # 2000K
            self._attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN  # 6500K
        elif "dimmable" in self._features:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes.add(ColorMode.ONOFF)
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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attributes = {}
        
        # Add DALI group membership information
        if self._groups:
            attributes["dali_groups"] = self._groups
            attributes["dali_group_count"] = len(self._groups)
        
        # Get current device data for additional info
        current_device = self._coordinator.get_device(self._device_id)
        if current_device:
            # Add DALI address and line information
            if "address" in current_device:
                attributes["dali_address"] = current_device["address"]
            if "line" in current_device:
                attributes["dali_line"] = current_device["line"]
            if "type" in current_device:
                attributes["dali_device_type"] = current_device["type"]
        
        return attributes

    def _is_optimistic_state_valid(self) -> bool:
        """Check if optimistic state is still valid (within time window)."""
        elapsed = time.time() - self._optimistic_timestamp
        is_valid = elapsed < 5.0  # 5 seconds window
        # Debug logging removed to reduce log spam
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
        # Check if light is currently on to decide whether to send switchable command
        current_is_on = self.is_on
        transition_time = kwargs.get(ATTR_TRANSITION)
        brightness_only = ATTR_BRIGHTNESS in kwargs and len([k for k in kwargs.keys() if k != ATTR_TRANSITION]) == 1
        
        # Optimistically update local state for immediate UI feedback
        self._optimistic_state["switchable"] = True
        self._optimistic_timestamp = time.time()
        
        if ATTR_BRIGHTNESS in kwargs:
            self._optimistic_state["brightness"] = kwargs[ATTR_BRIGHTNESS]
        
        # Optimistic state set (debug logging removed)
        
        # Force immediate UI update with optimistic state
        self.async_write_ha_state()
        
        # Prepare command data - only send switchable if light is off or explicit turn on
        data = {}
        
        # Only send switchable=True if light is currently off or it's not just a brightness change
        if not current_is_on or not brightness_only:
            data["switchable"] = True
        
        if ATTR_BRIGHTNESS in kwargs:
            data["dimmable"] = kwargs[ATTR_BRIGHTNESS] / 2.55
            
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            data["colorRGB"] = {
                "r": r / 255,
                "g": g / 255,
                "b": b / 255,
            }
            
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            data["colorKelvin"] = kwargs[ATTR_COLOR_TEMP_KELVIN]
        
        # Ensure we have at least one command to send
        if not data:
            _LOGGER.warning("Device %s: No command data to send", self._device_id)
            return
        
        # Sending command to device (debug logging removed)
        
        try:
            # Send command to device - use fade-enabled control if transition is specified
            if transition_time is not None:
                await self._coordinator.device.async_control_device_with_fade(
                    self._device_id, data, transition_time
                )
            else:
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
        transition_time = kwargs.get(ATTR_TRANSITION)
        
        # Optimistically update local state for immediate UI feedback
        self._optimistic_state["switchable"] = False
        self._optimistic_timestamp = time.time()
        
        # Force immediate UI update with optimistic state
        self.async_write_ha_state()
        
        data = {"switchable": False}
        
        try:
            # Send command to device - use fade-enabled control if transition is specified
            if transition_time is not None:
                await self._coordinator.device.async_control_device_with_fade(
                    self._device_id, data, transition_time
                )
            else:
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
        # Update group membership from current device data
        current_device = self._coordinator.get_device(self._device_id)
        if current_device:
            self._groups = current_device.get("groups", [])
        
        # Only clear optimistic state if it's older than the grace period
        if not self._is_optimistic_state_valid():
            self._optimistic_state.clear()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the light state."""
        await self._coordinator.async_request_refresh()


class Dali2IotGroupLight(LightEntity):
    """Representation of a DALI2 IoT group light."""

    def __init__(
        self,
        coordinator: Dali2IotCoordinator,
        group: dict[str, Any],
    ) -> None:
        """Initialize the group light."""
        self._coordinator = coordinator
        self._group = group
        self._group_id = group["id"]
        self._name = group["name"]
        self._members = group.get("members", [])
        self._features = group.get("features", {})
        
        # Cache for optimistic updates
        self._optimistic_state = {}
        self._optimistic_timestamp = 0.0
        
        # Set supported color modes based on group features
        self._attr_supported_color_modes = set()
        
        # Priority order: RGB > COLOR_TEMP > BRIGHTNESS > ONOFF
        if "colorRGB" in self._features:
            self._attr_supported_color_modes.add(ColorMode.RGB)
            self._attr_color_mode = ColorMode.RGB
        elif "colorKelvin" in self._features:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN
            self._attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN
        elif "dimmable" in self._features:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes.add(ColorMode.ONOFF)
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def name(self) -> str:
        """Return the name of the group."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the group."""
        return f"dali2_iot_group_{self._group_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._coordinator.device.device_info

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attributes = {
            "dali_group_id": self._group_id,
            "dali_group_members": [member["id"] for member in self._members],
            "dali_group_member_count": len(self._members),
            "dali_group_member_names": [member["name"] for member in self._members],
        }
        return attributes

    def _is_optimistic_state_valid(self) -> bool:
        """Check if optimistic state is still valid."""
        elapsed = time.time() - self._optimistic_timestamp
        return elapsed < 5.0  # 5 seconds window

    @property
    def is_on(self) -> bool:
        """Return true if group is on (if any member is on)."""
        # Check optimistic state first
        if "switchable" in self._optimistic_state and self._is_optimistic_state_valid():
            return self._optimistic_state["switchable"]
        
        # Check if any group member is on
        current_group = self._coordinator.get_group(self._group_id)
        if current_group:
            for member in current_group.get("members", []):
                device = self._coordinator.get_device(member["id"])
                if device and "features" in device:
                    if device["features"].get("switchable", {}).get("status", False):
                        return True
        return False

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the group (average of members)."""
        # Check optimistic state first
        if "brightness" in self._optimistic_state and self._is_optimistic_state_valid():
            return self._optimistic_state["brightness"]
        
        # Calculate average brightness of group members
        current_group = self._coordinator.get_group(self._group_id)
        if current_group:
            brightness_values = []
            for member in current_group.get("members", []):
                device = self._coordinator.get_device(member["id"])
                if device and "features" in device:
                    features = device["features"]
                    if "dimmable" in features:
                        dim_value = features["dimmable"].get("status", 0)
                        brightness_values.append(int(dim_value * 2.55))
            
            if brightness_values:
                return int(sum(brightness_values) / len(brightness_values))
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return RGB color (from first member that supports it)."""
        current_group = self._coordinator.get_group(self._group_id)
        if current_group:
            for member in current_group.get("members", []):
                device = self._coordinator.get_device(member["id"])
                if device and "features" in device:
                    features = device["features"]
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
        """Return color temperature (from first member that supports it)."""
        current_group = self._coordinator.get_group(self._group_id)
        if current_group:
            for member in current_group.get("members", []):
                device = self._coordinator.get_device(member["id"])
                if device and "features" in device:
                    features = device["features"]
                    if "colorKelvin" in features:
                        return int(features["colorKelvin"].get("status", 4000))
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the group on."""
        # Check if group is currently on to decide whether to send switchable command
        current_is_on = self.is_on
        transition_time = kwargs.get(ATTR_TRANSITION)
        brightness_only = ATTR_BRIGHTNESS in kwargs and len([k for k in kwargs.keys() if k != ATTR_TRANSITION]) == 1
        
        # Optimistic update
        self._optimistic_state["switchable"] = True
        self._optimistic_timestamp = time.time()
        
        if ATTR_BRIGHTNESS in kwargs:
            self._optimistic_state["brightness"] = kwargs[ATTR_BRIGHTNESS]
        
        self.async_write_ha_state()
        
        # Prepare command data - only send switchable if group is off or explicit turn on
        data = {}
        
        # Only send switchable=True if group is currently off or it's not just a brightness change
        if not current_is_on or not brightness_only:
            data["switchable"] = True
        
        if ATTR_BRIGHTNESS in kwargs:
            data["dimmable"] = kwargs[ATTR_BRIGHTNESS] / 2.55
            
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            data["colorRGB"] = {
                "r": r / 255,
                "g": g / 255,
                "b": b / 255,
            }
            
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            data["colorKelvin"] = kwargs[ATTR_COLOR_TEMP_KELVIN]
        
        # Ensure we have at least one command to send
        if not data:
            _LOGGER.warning("Group %s: No command data to send", self._group_id)
            return
        
        try:
            # Send command to group - much more efficient than individual devices!
            if transition_time is not None:
                await self._coordinator.device.async_control_group_with_fade(
                    self._group_id, data, transition_time
                )
            else:
                await self._coordinator.device.async_control_group(self._group_id, data)
            
            # Refresh coordinator data
            await self._coordinator.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error("Failed to turn on group %s: %s", self._group_id, err)
            self._optimistic_state.clear()
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the group off."""
        transition_time = kwargs.get(ATTR_TRANSITION)
        
        # Optimistic update
        self._optimistic_state["switchable"] = False
        self._optimistic_timestamp = time.time()
        
        self.async_write_ha_state()
        
        data = {"switchable": False}
        
        try:
            # Send command to group - use fade-enabled control if transition is specified
            if transition_time is not None:
                await self._coordinator.device.async_control_group_with_fade(
                    self._group_id, data, transition_time
                )
            else:
                await self._coordinator.device.async_control_group(self._group_id, data)
            
            # Refresh coordinator data
            await self._coordinator.async_request_refresh()
            
        except Exception as err:
            _LOGGER.error("Failed to turn off group %s: %s", self._group_id, err)
            self._optimistic_state.clear()
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self._on_coordinator_update)
        )
    
    def _on_coordinator_update(self) -> None:
        """Handle coordinator update."""
        # Update group data from coordinator
        current_group = self._coordinator.get_group(self._group_id)
        if current_group:
            self._members = current_group.get("members", [])
            self._features = current_group.get("features", {})
        
        # Clear optimistic state if expired
        if not self._is_optimistic_state_valid():
            self._optimistic_state.clear()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the group state."""
        await self._coordinator.async_request_refresh() 