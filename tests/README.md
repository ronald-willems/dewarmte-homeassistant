# DeWarmte integration tests

## Unit tests

Mocked tests, no network. `conftest.py` blocks sockets through `pytest-socket`, so a test that accidentally reaches the internet fails.

```bash
python -m pip install -r requirements_test.txt
python -m pytest tests/ -q
```

| File | Covers |
|------|--------|
| `test_status_data.py` | Parsing of the status response. |
| `test_auth_client.py` | Token refresh and request retry. |
| `test_config_flow.py` | The install screen, including the energy history default for new installs. |
| `test_cooling_settings.py` | Cooling settings and the `thermostat_type` rename. Also the reference for the stub style (`FakeResponse`, `RecordingSession`, `StubAuth`). |
| `test_heat_curve_settings.py` | Switching the heat curve between fixed and weather mode (#22). |
| `test_settings_write_response.py` | Entities update from the API's echo of a write instead of a poll. |
| `test_settings_state_sensor.py` | The Settings State sensor and the restore warning (#30). |
| `test_operating_state_sensor.py` | The Operating State sensor (#28). |
| `test_smart_control.py` | Pomp T smart heating control (#24). |
| `test_legionella_settings.py` | Pomp T legionella protection (#29). |
| `test_energy_integration_sensor.py` | Constructing the energy sensor on old and new Home Assistant cores (#21). |
| `test_energy_history.py` | Mapping DeWarmte's hourly buckets onto statistics hours, including DST days and gaps. |

## Against the real DeWarmte service

These need a `tests/secrets.yaml` with your MyDeWarmte credentials; copy `secrets.template.yaml`. Never commit it.

- `python -m pytest tests/ -q --use-real-website` runs the suite with sockets enabled, so tests that take the `real_credentials` fixture log in for real.
- `python tests/test_entity_retrieval.py` logs in, discovers devices and prints their status and settings. Read-only.
- `python tests/update_entity.py <entity_id> <new_state>` writes one setting through the API client, for example `select.dewarmte_sound_mode silent`. This changes your heat pump's settings.

For checking the live API without writing anything, prefer `scripts/probe-dewarmte-api.py`; the scripts for deploying to a Home Assistant and reading its logs are described in [AGENTS.md](../AGENTS.md).
