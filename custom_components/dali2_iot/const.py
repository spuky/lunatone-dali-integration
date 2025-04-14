"""Constants for the DALI2 IoT integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "dali2_iot"

# Configuration
CONF_HOST: Final = "host"
CONF_NAME: Final = "name"

# Defaults
DEFAULT_NAME: Final = "DALI2 IoT"
DEFAULT_PORT: Final = 80
DEFAULT_TIMEOUT: Final = 10

# Services
SERVICE_SET_SCENE: Final = "set_scene"
SERVICE_SET_FADE_TIME: Final = "set_fade_time"

# Attributes
ATTR_SCENE: Final = "scene"
ATTR_FADE_TIME: Final = "fade_time" 