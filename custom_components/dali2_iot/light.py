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


# DALI logarithmic curve table: Translate HA linear brightness (0-255) to Lunatone inverse DALI percentage
LUNATONE_PERCENT_BY_STEP: list[float] = [
     0.00, 20.08, 29.92, 35.83, 39.76, 43.31, 45.67, 48.03, 50.00, 51.57, 53.15,
    54.33, 55.91, 56.69, 57.87, 59.06, 59.84, 60.63, 61.42, 62.20, 62.99, 63.78,
    64.57, 64.96, 65.75, 66.14, 66.93, 67.32, 68.11, 68.50, 68.90, 69.29, 69.69,
    70.47, 70.87, 71.26, 71.65, 72.05, 72.44, 72.83, 73.23, 73.62, 73.62, 74.02,
    74.41, 74.80, 75.20, 75.59, 75.59, 75.98, 76.38, 76.77, 76.77, 77.17, 77.56,
    77.56, 77.95, 78.35, 78.35, 78.74, 79.13, 79.13, 79.53, 79.53, 79.92, 79.92,
    80.31, 80.71, 80.71, 81.10, 81.10, 81.50, 81.50, 81.89, 81.89, 82.28, 82.28,
    82.68, 82.68, 83.07, 83.07, 83.07, 83.46, 83.46, 83.86, 83.86, 84.25, 84.25,
    84.65, 84.65, 84.65, 85.04, 85.04, 85.43, 85.43, 85.43, 85.83, 85.83, 85.83,
    86.22, 86.22, 86.61, 86.61, 86.61, 87.01, 87.01, 87.01, 87.40, 87.40, 87.40,
    87.80, 87.80, 87.80, 88.19, 88.19, 88.19, 88.58, 88.58, 88.58, 88.98, 88.98,
    88.98, 88.98, 89.37, 89.37, 89.37, 89.76, 89.76, 89.76, 90.16, 90.16, 90.16,
    90.16, 90.55, 90.55, 90.55, 90.55, 90.94, 90.94, 90.94, 91.34, 91.34, 91.34,
    91.34, 91.73, 91.73, 91.73, 91.73, 92.13, 92.13, 92.13, 92.13, 92.52, 92.52,
    92.52, 92.52, 92.91, 92.91, 92.91, 92.91, 92.91, 93.31, 93.31, 93.31, 93.31,
    93.70, 93.70, 93.70, 93.70, 93.70, 94.09, 94.09, 94.09, 94.09, 94.49, 94.49,
    94.49, 94.49, 94.49, 94.88, 94.88, 94.88, 94.88, 94.88, 95.28, 95.28, 95.28,
    95.28, 95.28, 95.67, 95.67, 95.67, 95.67, 95.67, 95.67, 96.06, 96.06, 96.06,
    96.06, 96.06, 96.46, 96.46, 96.46, 96.46, 96.46, 96.85, 96.85, 96.85, 96.85,
    96.85, 96.85, 97.24, 97.24, 97.24, 97.24, 97.24, 97.24, 97.64, 97.64, 97.64,
    97.64, 97.64, 97.64, 98.03, 98.03, 98.03, 98.03, 98.03, 98.03, 98.43, 98.43,
    98.43, 98.43, 98.43, 98.43, 98.82, 98.82, 98.82, 98.82, 98.82, 98.82, 98.82,
    99.21, 99.21, 99.21, 99.21, 99.21, 99.21, 99.21, 99.61, 99.61, 99.61, 99.61,
    99.61, 99.61, 100.00
]

def _lunatone_to_brightness(percent: float) -> int:
    """Map device percent (0-100) to HA brightness (0-255) using nearest DALI step.

    Example: 90 -> 127 (50%)
    """


    if percent <= 0.0:
        return 0
    if percent >= 100.0:
        return 255
    import bisect
    pos = bisect.bisect_left(LUNATONE_PERCENT_BY_STEP, percent)
    left = max(pos - 1, 0)
    right = min(pos, 255)
    step = right if abs(LUNATONE_PERCENT_BY_STEP[right] - percent) < abs(LUNATONE_PERCENT_BY_STEP[left] - percent) else left


    return int(step)

def _brightness_to_lunatone(brightness: int) -> float:
    """Map HA brightness (0-255) to Lunatone brightness value.

    Brightness 255 is coerced to step 100.
    """


    if brightness <= 0:
        return 0.0
    if brightness >= 255:
        step = 255
    else:
        step = max(0, min(255, brightness))


    return LUNATONE_PERCENT_BY_STEP[step]




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
                return _lunatone_to_brightness(dim_value)  # Convert 0-100 to 0-255
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
        
        # Only send switchable=True if light is currently off or it's not just a brightness change, setting a brightness turns the light implicitly on
        if (not current_is_on or not brightness_only) and not ATTR_BRIGHTNESS in kwargs:
            data["gotoLastActive"] = True # Trun on at last active brightness level 
        #    data["switchable"] = True
        
        if ATTR_BRIGHTNESS in kwargs:
            data["dimmable"] = _brightness_to_lunatone(kwargs[ATTR_BRIGHTNESS])
            
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
                        brightness_values.append(_lunatone_to_brightness(dim_value))
            
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
        
        # Only send switchable=True if group is currently off or it's not just a brightness change, setting a brightness turns the light implicitly on
        if (not current_is_on or not brightness_only) and not ATTR_BRIGHTNESS in kwargs:
            data["gotoLastActive"] = True # Trun on at last active brightness level 
        #    data["switchable"] = True
        
        if ATTR_BRIGHTNESS in kwargs:
            data["dimmable"] = _brightness_to_lunatone(kwargs[ATTR_BRIGHTNESS])
            
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