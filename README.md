# Home Assistant DALI2 IoT Integration

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

1. Go to Home Assistant's Configuration > Integrations
2. Click the "+" button to add a new integration
3. Search for "DALI2 IoT"
4. Enter the following information:
   - Host: IP address of your DALI2 IoT device
   - Port: Port number (default: 80)
   - Username: Device username (default: admin)
   - Password: Device password

## Features

- Control DALI2 IoT lights
- Brightness control
- On/Off control

## Development

This integration is under active development. Feel free to contribute by submitting issues or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 