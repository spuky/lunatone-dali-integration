"""Discovery module for DALI2 IoT integration."""
from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Any, Final

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DISCOVERY_PORT: Final = 5555
DISCOVERY_MESSAGE: Final = '{"type": "discovery"}'
DISCOVERY_TIMEOUT: Final = 5.0

class Dali2IotDiscovery:
    """Class to handle discovery of DALI2 IoT devices."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the discovery."""
        self._socket: socket.socket | None = None
        self._hass = hass

    async def discover(self) -> list[dict[str, Any]]:
        """Discover DALI2 IoT devices in the network."""
        devices: list[dict[str, Any]] = []
        
        _LOGGER.info("Starting DALI2 IoT discovery")
        
        # Create UDP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socket.settimeout(DISCOVERY_TIMEOUT)
        
        try:
            _LOGGER.info("Sending discovery broadcast to port %s", DISCOVERY_PORT)
            # Send broadcast message
            self._socket.sendto(
                DISCOVERY_MESSAGE.encode(),
                ("<broadcast>", DISCOVERY_PORT)
            )
            
            _LOGGER.info("Waiting for responses for %s seconds", DISCOVERY_TIMEOUT)
            # Wait for responses
            while True:
                try:
                    data, addr = self._socket.recvfrom(1024)
                    _LOGGER.info("Received response from %s: %s", addr[0], data.decode())
                    response = json.loads(data.decode())
                    
                    if response.get("type") == "dali-2-iot":
                        device_info = {
                            "host": addr[0],
                            "name": response.get("name", "DALI2 IoT"),
                        }
                        _LOGGER.info("Discovered DALI2 IoT device: %s", device_info)
                        devices.append(device_info)
                    else:
                        _LOGGER.warning("Received unexpected response type from %s: %s", addr[0], response)
                except socket.timeout:
                    _LOGGER.info("Discovery timeout reached")
                    break
                except (json.JSONDecodeError, UnicodeDecodeError) as err:
                    _LOGGER.warning("Invalid response from %s: %s", addr[0], err)
                    continue
                    
        except Exception as err:
            _LOGGER.error("Error during discovery: %s", err)
        finally:
            if self._socket:
                self._socket.close()
                self._socket = None
                
        _LOGGER.info("Discovery complete. Found %d devices", len(devices))
        return devices 