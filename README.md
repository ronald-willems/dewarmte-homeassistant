# dewarmte-homeassistant
Home Assistant Plugin for DeWarmte

This custom integration allows you to control and monitor your DeWarmte PompAO through Home Assistant by using api.mydewarmte.com

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


Feel free to contribute by creating issues or pull requests.

## Next:

