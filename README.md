# Home Assistant DALI2 IoT Integration

⚠️ **WORK IN PROGRESS** ⚠️

A Home Assistant custom integration for controlling DALI2 IoT devices via network communication. This integration is under active development and testing.

## Current Status
- Device communication and control ✅ (Basic functionality working)
- Automatic UDP discovery ✅ (Working)
- Manual configuration ✅ (Working)
- Light entities with responsive UI ✅ (Working with optimizations)
- Device scanning ✅ (Working)
- Brightness control ✅ (Optimized to reduce flickering)
- Service and UI-based device discovery ✅ (Working)
- Group membership visibility ✅ (Shows which DALI groups each device belongs to)
- Group management services ✅ (Add/remove devices from DALI groups)
- DALI group entities ✅ (Control entire groups as individual light entities)
- Fade time control ✅ (Smooth transitions with DALI native fade support)
- RGB/Color temperature support ⚠️ (Implemented but needs testing)
- Error handling ⚠️ (Basic implementation, needs improvement)
- Production stability ❌ (Still in development/testing phase)

## Features

### Device Discovery & Configuration
- **Automatic UDP Discovery**: Automatically finds DALI2 IoT controllers on your network (UDP port 5555)
- **Manual Configuration**: Enter device IP address manually if auto-discovery doesn't work
- **Multi-device Support**: Support for multiple DALI2 IoT controllers

### Light Control
- **Responsive UI**: Immediate visual feedback with optimistic updates (5-second grace period)
- **Brightness Control**: Smooth dimming without unwanted light flashing
- **On/Off Control**: Reliable switching with proper state management
- **Group Control**: Control entire DALI groups as single entities for efficient operation
- **Feature Detection**: Automatically detects and enables only supported features:
  - Dimmable lights (brightness control)
  - RGB color control (if supported by device)
  - Color temperature control (if supported by device)

### Device Management
- **DALI Bus Scanning**: Scan for new devices directly from Home Assistant
- **UI Options**: Access scan functionality through integration options
- **Service Integration**: `dali2_iot.scan_devices` service for automation
- **New Installation Mode**: Option to clear existing devices before scanning
- **Group Management**: Add/remove devices from DALI groups via services
- **Real-time Updates**: Group membership changes reflect immediately in device attributes

### Technical Features
- **Optimistic Updates**: UI responds immediately to commands while maintaining data consistency
- **Intelligent Control**: Only sends necessary commands (e.g., brightness-only changes don't trigger switchable commands)
- **Group Information**: Device attributes show DALI group membership, addresses, and line information
- **Efficient Group Control**: Single API calls control multiple devices simultaneously via DALI groups
- **Smart Status Aggregation**: Group entities intelligently combine member device states
- **Error Handling**: Comprehensive error handling with detailed logging
- **State Coordination**: 30-second data refresh with smart state merging

## Installation

### HACS (Recommended)
1. Add this repository as a custom repository in HACS
2. Install "DALI2 IoT Integration" through HACS
3. Restart Home Assistant

### Manual Installation
1. Copy the `custom_components/dali2_iot` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Automatic Discovery (Recommended)
1. Navigate to **Settings** > **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "DALI2 IoT"
4. If devices are found automatically, select your device from the list
5. Click **Submit** to complete setup

### Manual Configuration

If automatic discovery does not work for example your device is in a different subnet, 
you can manually configure the integration:

1. Navigate to **Settings** > **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "DALI2 IoT"
4. Choose Manual entry... 
5. Enter your DALI2 IoT controller's IP address
6. Provide a name for the device (optional)
7Click **Submit**

## Device Management

### Scanning for New DALI Devices

#### Via Integration Options (UI Method)
1. Go to **Settings** > **Devices & Services**
2. Find your DALI2 IoT integration
3. Click **Configure**
4. Enable **Scan for new DALI devices**
5. Optionally enable **New installation** to clear existing devices
6. Click **Submit** to start scan

#### Via Service Call
Use the `dali2_iot.scan_devices` service:
```yaml
service: dali2_iot.scan_devices
data:
  new_installation: false  # Set to true to clear existing devices
```

### Viewing Device Group Information

Each DALI device displays additional information in its attributes:
- **dali_groups**: List of DALI group IDs the device belongs to
- **dali_group_count**: Number of groups the device is in
- **dali_address**: DALI bus address of the device
- **dali_line**: DALI line number
- **dali_device_type**: Type of DALI device

To view this information:
1. Go to **Developer Tools** > **States**
2. Find your DALI light entity (e.g., `light.dali_device_1`)
3. Click on it to see the attributes

### Managing DALI Group Memberships

The integration provides services to manage which DALI groups devices belong to:

#### Add Device to Group
```yaml
service: dali2_iot.add_to_group
data:
  device_id: 1      # DALI device ID (0-63)
  group_id: 5       # DALI group ID (0-15)
```

#### Remove Device from Group
```yaml
service: dali2_iot.remove_from_group
data:
  device_id: 1      # DALI device ID (0-63)
  group_id: 5       # DALI group ID (0-15)
```

#### Set All Group Memberships
```yaml
service: dali2_iot.update_device_groups
data:
  device_id: 1      # DALI device ID (0-63)
  groups: [1, 3, 5] # List of group IDs the device should belong to
```

**Note**: Group changes are reflected immediately in the device attributes and take effect on the DALI bus.

### DALI Group Entities

DALI groups automatically appear as individual light entities in Home Assistant when they contain devices. This provides several advantages:

#### **Efficient Control**
- Control multiple devices with a single API call to `/group/{id}/control`
- All devices in the group change simultaneously
- Much faster than controlling individual devices separately

#### **Smart Status Aggregation**
- **Group is ON**: If any member device is on
- **Group Brightness**: Average brightness of all member devices
- **Group Colors**: Uses RGB/temperature from the first capable device

#### **Group Entity Attributes**
Each DALI group entity shows:
- `dali_group_id`: The DALI group ID (0-15)
- `dali_group_members`: List of member device IDs
- `dali_group_member_count`: Number of devices in the group
- `dali_group_member_names`: Names of all member devices

#### **Usage Example**
Groups appear automatically in Home Assistant as `light.dali_group_X` entities. Simply control them like any other light:

```yaml
# Turn on all lights in group 5 to 80% brightness
service: light.turn_on
target:
  entity_id: light.dali_group_5
data:
  brightness_pct: 80
```

### DALI Fade Time Control

Control smooth lighting transitions with DALI-native fade support for professional lighting effects.

#### **Standard Home Assistant Transition**
Use the standard `transition` parameter with any light command:

```yaml
# Smooth dimming over 3 seconds
service: light.turn_on
target:
  entity_id: light.dali_device_1
data:
  brightness_pct: 80
  transition: 3

# Color change with 2-second fade (groups work too!)
service: light.turn_on
target:
  entity_id: light.dali_group_5
data:
  rgb_color: [255, 100, 0]
  transition: 2

# Smooth turn off over 1.5 seconds
service: light.turn_off
target:
  entity_id: light.dali_device_2
data:
  transition: 1.5
```

#### **Set Device Fade Time**
Configure default fade time for devices and groups:

```yaml
# Set fade time for individual device
service: dali2_iot.set_fade_time
data:
  device_id: 3        # DALI device ID
  fade_time: 1.5      # Fade time in seconds (0.0 - 60.0)

# Set fade time for entire group
service: dali2_iot.set_group_fade_time
data:
  group_id: 5         # DALI group ID  
  fade_time: 2.0      # Fade time in seconds
```

#### **Technical Features**
- **DALI-Native**: Uses actual DALI `*WithFade` API parameters
- **Intelligent Conversion**: Automatically converts standard commands to fade variants
- **Both Approaches**: Per-command transitions + global device settings
- **Full Support**: Works with brightness, RGB colors, color temperature
- **Group Compatible**: All fade features work with DALI groups

## API Endpoints

The integration communicates with DALI2 IoT controllers using these HTTP endpoints:
- `GET /info` - Device information
- `GET /devices` - List of DALI devices
- `POST /devices/{id}` - Control device
- `POST /scan` - Start device scan
- `GET /scan/status` - Get scan status

## Network Requirements

- DALI2 IoT controller must be accessible via HTTP on your network
- UDP port 5555 must be open for auto-discovery
- Home Assistant and DALI2 IoT controller should be on the same network segment for optimal discovery

## DALI-2 IoT Device Features

The DALI-2 IoT controller has many advanced features. This integration currently implements core lighting control and group management, with additional features planned for future releases.

### ✅ **Implemented Features**
- **Device Discovery & Control**: Full DALI device detection and individual control
- **DALI Groups**: Complete group management with entities and services
- **Device Scanning**: Automated DALI bus scanning with new installation mode
- **Basic Light Control**: On/off, dimming, RGB color, color temperature
- **Fade Time Control**: Smooth transitions with DALI-native fade support
- **Group Membership Management**: Add/remove devices from groups via services
- **Real-time Status**: Device and group state monitoring with optimistic updates

### 🚧 **Not implemented Features **
(developer has no need for them feel to ask for Features you need and have Hardware to test them)

#### **Virtual Zones**
The DALI-2 IoT device supports virtual zones (different from DALI groups):
- Custom zone creation with mixed device types
- Zone-based control and automation
- API endpoints: `/zones`, `/zone/{id}`, `/zone/{id}/control`

#### **Advanced Automation System**
The device includes a powerful built-in automation engine:
- **Trigger-Actions**: Event-based automation rules
- **Circadian Lighting**: Automatic color temperature adjustment based on time
- **Scheduler**: Time-based lighting schedules and scenes
- **Sequencer**: Complex lighting sequences and effects
- API endpoints: `/automations/*`, various automation management endpoints

#### **Sensor Integration**
Built-in sensor support for environmental control:
- Motion sensors, light sensors, temperature sensors
- Sensor-triggered automation
- API endpoints: `/sensors`, `/sensors/{id}`

#### **Scene Management**
Advanced scene control beyond basic on/off:
- DALI scene programming and recall
- Scene-based automation integration
- Custom scene creation and management

#### **Enhanced Device Features**
Additional DALI device capabilities:
- ✅ **Fade time control** - Implemented with full DALI native support
- Scene setting and recall
- Advanced color control features
- Device-specific configuration options

#### **System Management**
Advanced controller management:
- Email notifications and alerts
- System monitoring and diagnostics
- Advanced network configuration
- Backup and restore functionality

### 📝 **Contributing**

Interested in implementing any of these features? The DALI-2 IoT API documentation is available in `/Doku/openapi.json`, and contributions are welcome!

## Troubleshooting

### Discovery Issues
- Ensure DALI2 IoT controller and Home Assistant are on the same network
- Check that UDP port 5555 is not blocked by firewall
- Try manual configuration with the device's IP address

### Connection Problems
- Verify the IP address is correct and device is powered on
- Check network connectivity between Home Assistant and device
- Review Home Assistant logs for detailed error messages

### Missing Light Entities
- Ensure DALI devices are properly connected to the bus
- Run a device scan to detect new devices
- Check that devices have required features (dimmable, switchable)

## Development

This integration is under active development and testing. While basic functionality works, it should be considered experimental. Use at your own risk and please report any issues you encounter. 

### Key Components
- `device.py` - Core device communication
- `coordinator.py` - Data coordination and caching  
- `light.py` - Light entity implementation with optimistic updates
- `config_flow.py` - Configuration and options flow
- `discovery.py` - UDP auto-discovery implementation

## License

This project is licensed under the MIT License - see the LICENSE file for details.
