# DeWarmte Integration for Home Assistant (unofficial)

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![HACS Action](https://github.com/ronald-willems/dewarmte-homeassistant/actions/workflows/validate.yaml/badge.svg)](https://github.com/ronald-willems/dewarmte-homeassistant/actions/workflows/validate.yaml)
[![Validate with hassfest](https://github.com/ronald-willems/dewarmte-homeassistant/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/ronald-willems/dewarmte-homeassistant/actions/workflows/hassfest.yaml)

This integration allows you to control and monitor your DeWarmte heat pump system through Home Assistant.

This integration is *not* an official integration of DeWarmte. Please reach out for issues and requests using github issues.
 

## Features

- Monitor heat pump status
- View energy consumption
- Adjust heat curves
- Adjust settings

Not working yet:
- cooling controls
- Other devices than PompAO


## Installation

### HACS 

1. Install [HACS](https://hacs.xyz/) if you haven't already
2. Go to HACS
3. Click menu button in top left and click on Custom Repositories
4. Add https://github.com/ronald-willems/dewarmte-homeassistant
5. Choose integration
6. Click Download
7. Go to Settings=>Devices&Services
8. Click on 'Add integration'
9. Search for 'DeWarmte'
10. Click install
11. Provide username and password for MyDewarmte app / web.
12. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/dewarmte` directory to your Home Assistant's `custom_components` directory
2. Go to Settings=>Devices&Services
3. Click on 'Add integration'
4. Search for 'DeWarmte'
5. Click install
6. Provide username and password for MyDewarmte app / web.
7. Restart Home Assistant



## Entities

The integration provides the following entities:

### Sensors
- Water Flow
- Supply Temperature
- Outdoor Temperature
- Heat Input
- Actual Temperature
- Electricity Consumption
- Heat Output
- Gas Boiler Status
- Thermostat Status
- Target Temperature
- Electric Backup Usage

### Numbers
- Heat Curve S1 Outside Temperature
- Heat Curve S1 Target Temperature
- Heat Curve S2 Outside Temperature
- Heat Curve S2 Target Temperature
- Heat Curve Fixed Temperature
- Heating Performance Backup Temperature
- Cooling Temperature

### Selects
- Heat Curve Mode
- Heating Kind
- Heating Performance Mode
- Sound Mode
- Sound Compressor Power
- Sound Fan Speed
- Advanced Thermostat Delay
- Backup Heating Mode
- Cooling Thermostat Type
- Cooling Control Mode

### Switches
- Boost Mode

## Troubleshooting

If you encounter any issues:

1. Check your credentials
2. Verify your internet connection
3. Check the Home Assistant logs
4. [Open an issue](https://github.com/ronald-willems/dewarmte-homeassistant/issues) if needed

## Development

To contribute to this integration:

1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

[commits-shield]: https://img.shields.io/github/commit-activity/y/ronald-willems/dewarmte-homeassistant.svg
[commits]: https://github.com/ronald-willems/dewarmte-homeassistant/commits/main
[releases-shield]: https://img.shields.io/github/release/ronald-willems/dewarmte-homeassistant.svg
[releases]: https://github.com/ronald-willems/dewarmte-homeassistant/releases

