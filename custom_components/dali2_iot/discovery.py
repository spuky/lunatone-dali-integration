"""Discovery module for DALI2 IoT integration."""
from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Any, Final

_LOGGER = logging.getLogger(__name__)

DISCOVERY_PORT: Final = 5555
DISCOVERY_MESSAGE: Final = '{"type": "discovery"}'
DISCOVERY_TIMEOUT: Final = 5.0

class Dali2IotDiscovery:
    """Class to handle discovery of DALI2 IoT devices."""

    def __init__(self) -> None:
        """Initialize the discovery."""
        self._socket: socket.socket | None = None

    async def discover(self) -> list[dict[str, Any]]:
        """Discover DALI2 IoT devices in the network."""
        devices: list[dict[str, Any]] = []
        
        # Create UDP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socket.settimeout(DISCOVERY_TIMEOUT)
        
        try:
            # Send broadcast message
            self._socket.sendto(
                DISCOVERY_MESSAGE.encode(),
                ("<broadcast>", DISCOVERY_PORT)
            )
            
            # Wait for responses
            while True:
                try:
                    data, addr = self._socket.recvfrom(1024)
                    response = json.loads(data.decode())
                    
                    if response.get("type") == "dali-2-iot":
                        devices.append({
                            "host": addr[0],
                            "name": response.get("name", "DALI2 IoT"),
                        })
                except socket.timeout:
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
                
        return devices 