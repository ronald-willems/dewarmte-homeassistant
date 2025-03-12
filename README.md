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

To set up the development environment:

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```
3. Copy `tests/secrets.template.yaml` to `tests/secrets.yaml` and fill in your credentials
4. Run tests: `python -m pytest tests/`

Note: The test suite requires Python 3.8 or higher and uses async/await functionality.

Future features planned:
- More detailed system information
- Control capabilities
- Historical data tracking

Feel free to contribute by creating issues or pull requests.

## Next:
LET OP: GIT niet goed in sync!! Ik  heb checkout gedaan (detached). Wat is dat?

Lets ad some more home assistant entities to this project. There is another page that contains numbers that can be edited. The page has the same url as the dashboard page, with only one difference: 'dashboard' should be replaced by 'heating'. 

Find the numbers on the page an make entities of those in homeassistant. Don't add any extra switches. Only numbers
