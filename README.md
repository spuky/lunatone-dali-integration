# Home Assistant DALI2 IoT Integration

⚠️ **WARNING: WORK IN PROGRESS** ⚠️

This integration is currently under development and is not yet functional. The basic structure is in place, but the actual device communication and control features are not yet implemented.

## Current Status
- Basic integration structure ✅
- HACS compatibility ✅
- Device communication ❌ (Not implemented)
- Light control ❌ (Not implemented)
- Configuration flow ✅ (Basic structure)
- Auto-discovery ✅ (Basic structure)

This is a custom integration for Home Assistant to control DALI2 IoT devices.

## Installation

1. Using HACS (Home Assistant Community Store):
   - Add this repository as a custom repository in HACS
   - Install the integration through HACS
   - Restart Home Assistant

2. Manual installation:
   - Copy the `custom_components/dali2_iot` directory to your Home Assistant's `custom_components` directory
   - Restart Home Assistant

## Configuration

The integration can be configured in two ways:

### Auto-discovery (Recommended)
1. Go to Home Assistant's Configuration > Integrations
2. Click the "+" button to add a new integration
3. Search for "DALI2 IoT"
4. If a DALI2 IoT device is found on your network, it will appear in the list
5. Click on the device to add it

### Manual Configuration
1. Go to Home Assistant's Configuration > Integrations
2. Click the "+" button to add a new integration
3. Search for "DALI2 IoT"
4. Select "Configure manually"
5. Enter the IP address of your DALI2 IoT device

## Features

- Control DALI2 IoT lights
- Brightness control
- On/Off control

## Development

This integration is under active development. Feel free to contribute by submitting issues or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 