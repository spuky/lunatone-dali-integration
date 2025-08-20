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
SERVICE_ADD_TO_GROUP: Final = "add_to_group"
SERVICE_REMOVE_FROM_GROUP: Final = "remove_from_group"
SERVICE_UPDATE_DEVICE_GROUPS: Final = "update_device_groups"
SERVICE_SET_FADE_TIME: Final = "set_fade_time"
SERVICE_SET_GROUP_FADE_TIME: Final = "set_group_fade_time"

# Attributes
ATTR_SCENE: Final = "scene"
ATTR_FADE_TIME: Final = "fade_time"
ATTR_DEVICE_ID: Final = "device_id"
ATTR_GROUP_ID: Final = "group_id"
ATTR_GROUPS: Final = "groups"

# Config Flow Options
MANUAL_ENTRY_TRANSLATION_KEY = "manual_entry"
