"""Light platform for DALI2 IoT integration."""
from __future__ import annotations

import logging
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
        if device.get("type") == "device":  # Only create lights for actual devices
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

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._device.get("switchable", False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        if "dimmable" in self._features:
            return int(self._device.get("dimmable", 0) * 2.55)
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color of the light."""
        if "colorRGB" in self._features:
            color = self._device.get("colorRGB", {})
            return (
                int(color.get("r", 0) * 255),
                int(color.get("g", 0) * 255),
                int(color.get("b", 0) * 255),
            )
        return None

    @property
    def color_temp(self) -> int | None:
        """Return the color temperature of the light."""
        if "colorKelvin" in self._features:
            return int(self._device.get("colorKelvin", 4000))
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
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
            
        await self._coordinator.device.async_control_device(self._device_id, data)
        await self._coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        data = {"switchable": False}
        await self._coordinator.device.async_control_device(self._device_id, data)
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self) -> None:
        """Update the light state."""
        await self._coordinator.async_request_refresh() 