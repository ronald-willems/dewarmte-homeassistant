# dewarmte-homeassistant
Home Assistant Plugin for DeWarmte

This custom integration allows you to control and monitor your DeWarmte system through Home Assistant by scraping data from mydewarmte.com.

## Installation

1. Copy the `custom_components/dewarmte` directory to your Home Assistant's `custom_components` directory.
2. Restart Home Assistant.
3. Go to Settings -> Devices & Services -> Add Integration
4. Search for "DeWarmte" and add it
5. Enter your mydewarmte.com credentials

## Configuration

The integration requires the following configuration:
- Email: Your mydewarmte.com email address
- Password: Your mydewarmte.com password
- Update Interval: How often to check for updates (in seconds)

## Features

- Temperature sensor showing current system temperature
- System status monitoring
- Automatic updates based on configured interval
- Secure credential storage

## Development

This is a work in progress. The integration currently supports:
- Website scraping from mydewarmte.com
- Temperature monitoring
- System status monitoring

Future features planned:
- More detailed system information
- Control capabilities
- Historical data tracking

Feel free to contribute by creating issues or pull requests.

## Next:
Lets ad some more home assistant entities to this project. There is another page that contains numbers that can be edited. The page has the same url as the dashboard page, with only one difference: 'dashboard' should be replaced by 'heating'. 

Find the numbers on the page an make entities of those in homeassistant. Don't add any extra switches. Only numbers
