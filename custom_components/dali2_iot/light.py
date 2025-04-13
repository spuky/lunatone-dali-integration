"""Support for DALI2 IoT lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DALI2 IoT light platform."""
    # TODO: Create your light entities here
    # This is where you would create instances of your light entities
    # based on the configuration
    pass

class Dali2IotLight(LightEntity):
    """Representation of a DALI2 IoT light."""

    def __init__(self, name: str, unique_id: str) -> None:
        """Initialize the light."""
        self._name = name
        self._unique_id = unique_id
        self._state = False
        self._brightness = 255
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the light."""
        return self._unique_id

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._state

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        # TODO: Implement actual turn on command
        self._state = True
        self._brightness = brightness

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # TODO: Implement actual turn off command
        self._state = False 