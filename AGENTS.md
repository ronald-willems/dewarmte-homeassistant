# Agents.md (for AI coding agents)

This repository is a Home Assistant **custom integration** for DeWarmte (`custom_components/dewarmte`). Future agent work should follow Home Assistant’s developer best practices and keep CI (HACS + hassfest) green.

## Repository map (high-signal)

- `custom_components/dewarmte/`
  - `manifest.json`: integration metadata, requirements, config flow enabled.
  - `__init__.py`: integration setup, creates `DeWarmteDataUpdateCoordinator` per discovered device.
  - `config_flow.py`: UI setup flow (username/password + update interval).
  - Platforms: `sensor.py`, `binary_sensor.py`, `number.py`, `select.py`, `switch.py`, `climate.py`
  - `api/`: DeWarmte API client (`aiohttp`), auth, OpenAPI spec, models.
  - `translations/en.json`: strings for config flow / UI.
- CI:
  - `.github/workflows/hassfest.yaml`: runs Home Assistant hassfest validation.
  - `.github/workflows/validate.yaml`: runs HACS action validation.
- Docs/tests:
  - `docs/README.md`
  - `tests/README.md` (includes optional “real website” scripts using `tests/secrets.yaml`)

## Non-negotiables (Home Assistant best practices)

Before implementing anything, read the relevant Home Assistant developer docs and follow them exactly:

- **Integration file structure**: `https://developers.home-assistant.io/docs/creating_integration_file_structure/`
- **Integration manifest**: `https://developers.home-assistant.io/docs/creating_integration_manifest/`
- **Config flows**: `https://developers.home-assistant.io/docs/config_entries_config_flow_handler/`
- **Fetching data / DataUpdateCoordinator**: `https://developers.home-assistant.io/docs/integration_fetching_data/`
- **Blocking operations with asyncio**: `https://developers.home-assistant.io/docs/asyncio_blocking_operations/`
- **Entity model & rules (no I/O in properties, unique_id patterns, device_info, etc.)**: `https://developers.home-assistant.io/docs/core/entity/`
- **Platform specifics (when changing entity behavior)**:
  - Climate: `https://developers.home-assistant.io/docs/core/entity/climate/`
  - Binary sensor: `https://developers.home-assistant.io/docs/core/entity/binary-sensor/`

### Async + I/O rules (must follow)

- **Never block the event loop**. No `time.sleep`, no synchronous network I/O, no disk I/O in async context. If something is blocking, use `await hass.async_add_executor_job(...)` as per the asyncio blocking guide.
- **Prefer async-native libraries** (this integration already uses `aiohttp` internally). Avoid adding new synchronous HTTP usage.
- **No network calls in entity properties**. Properties (like `native_value`, `is_on`, `current_option`, etc.) must return in-memory values (usually from coordinator data / cached settings).

## Integration-specific constraints (read this before changing code)

- **Multi-device setup**: `async_setup_entry` discovers devices and creates **one coordinator per device**, stored as a list in `hass.data[DOMAIN][entry.entry_id]`. Several platforms accept both a list and a single coordinator for backward compatibility—preserve this behavior unless you migrate it carefully.
- **Coordinator responsibilities**:
  - Polling returns `StatusData` via `_async_update_data`.
  - Settings are currently cached on the coordinator as `_cached_settings` for some device types.
  - Entities should read from `coordinator.data` and/or cached settings only.
- **Unique IDs must remain stable**: current entities use `f"{device_id}_{key}"`. If you rename keys, entity ids may change (breaking user dashboards/automations). If you must change entity identity, implement a migration strategy.
  - Precedent: when DeWarmte renamed the API field `cooling_thermostat_type` → `thermostat_type`, we kept the internal name (and entity key) `cooling_thermostat_type` and translated only at the API boundary (`from_api_response` reads `thermostat_type`; the cooling POST writes it back). Prefer this "map at the API layer" pattern over renaming entities.
- **Be careful with “AO/MP/PT/HC” device-type gating**: platforms filter entities based on `device.device_type` and some also check `product_id.startswith(("AO ", "MP ", "PT "))`. Maintain backward compatibility unless you can prove it’s safe.
- **Don’t store secrets**: test scripts may use a local `tests/secrets.yaml`. Never commit credentials; avoid printing secrets to logs.

## When editing config flow

Use the config flow docs as the source of truth:

- Support reauth/unique_id patterns where applicable (see `config_entries_config_flow_handler` docs).
- Ensure errors map to translation keys in `custom_components/dewarmte/translations/en.json`.
- Avoid calling “private” methods across modules unless there’s no alternative (e.g., avoid relying on internal auth methods unless you have to).

## When editing entities

Follow entity docs and platform docs:

- Use `CoordinatorEntity` for coordinator-driven updates.
- Keep entity properties cheap and deterministic; update state in `_handle_coordinator_update` only when needed.
- Set `_attr_has_entity_name = True` (already common here) and ensure `_attr_device_info` is set for device registry consistency.
- Entity names are set directly (`name=` in descriptions or `_attr_name`); `translations/en.json` covers the config/options flow, not entity names.

## Local dev loop: test → deploy → read logs

This section captures the working commands + gotchas so you don't rediscover them. Config lives in `tests/secrets.yaml` (DeWarmte creds), root `secrets.yaml` (`ha_samba_*`, `ha_api_token`), and `deploy.local.yaml` (`ha_samba_host`, `ha_api_url`). Use the repo `.venv`.

**1. Unit tests**
```bash
python -m pip install -r requirements_test.txt   # includes pytest-socket (conftest needs it)
python -m pytest tests/ -q
```
- `conftest.py` blocks sockets for mock tests; `--use-real-website` enables live calls.
- Stub style: `FakeResponse` / `RecordingSession` (records POST bodies) / `StubAuth` — see `tests/test_cooling_settings.py`.

**2. Verify parsing against the LIVE API (read-only, no writes)**
```bash
python scripts/probe-dewarmte-api.py
```
Logs in with `tests/secrets.yaml` and runs real responses through the actual client/parsers. **Run this first whenever users report breakage after a DeWarmte-side change** — a `settings parsed: FAILED` means the response schema shifted.

**3. Deploy to a real Home Assistant (SMB upload + restart)**
```bash
bash scripts/deploy-homeassistant.sh && bash scripts/ha-wait-ready.sh
```
- **Gotcha:** after the restart the API returns 200 within ~2s while only ~12 entities exist (early boot). Do **not** inspect entities yet — `ha-wait-ready.sh` polls until the entity count stabilizes (~25-30s).

**4. Read logs**
```bash
bash scripts/ha-logs.sh            # recent lines mentioning dewarmte
bash scripts/ha-logs.sh writes     # settings-write trail (POST bodies + responses/errors)
```
- **Gotcha:** `/api/error_log` returns 404 here and there is no writable `/config/home-assistant.log` (Core logs to the journal). The scripts read `/api/hassio/core/logs` via the long-lived token, which includes the integration's DEBUG lines.
- The client already logs at DEBUG (request URLs + bodies). To force the level at runtime (resets on restart):
  `POST /api/services/logger/set_level` body `{"custom_components.dewarmte":"debug"}`.
- A HAR file cannot capture HA's traffic (HA is a backend, not a browser); use the logs. HARs only capture the mydewarmte.com web app in a browser.

**Investigating a DeWarmte API change:** the web app at `mydewarmte.com` is a Flutter app. Fetch `https://mydewarmte.com/main.dart.js` and grep it for field names / endpoint paths (e.g. `settings/`, `thermostat_type`, `start-forced`) to see the current request/response schema the official client uses.

**Which values does a settings field accept?** The backend is Django REST Framework, so an authenticated `OPTIONS` on a write endpoint returns the field metadata — including the authoritative list of choices, without writing anything:

```
OPTIONS /v1/customer/products/{deviceId}/settings/cooling/
  -> actions.POST.cooling_control_mode.choices = [scheduled, thermostat, heating_only, cooling_only]
```

Use this before assuming an enum value is valid: these vocabularies change (`manual` was retired around May 2025, `forced` some time after — see the `cooling_control_mode` note in `openapi.yaml`). Only the write endpoints expose `actions`; `OPTIONS` on the read-only `settings/` returns nothing useful.

## Testing and validation (local)

This repo’s CI runs:

- **hassfest** (metadata/manifest checks)
- **HACS action** (HACS validation rules)

Suggested local checks:

- Install deps:
  - `python -m pip install -r requirements.txt`
  - `python -m pip install -r requirements_test.txt`
- Run tests:
  - `pytest -v`

Notes:

- `tests/README.md` describes optional scripts that hit the real DeWarmte service using a local `tests/secrets.yaml`. These are for manual verification only.

## How to work effectively in this repo (agent guidance)

- Start by identifying the platform(s) affected (`sensor.py`, `climate.py`, etc.) and whether the change touches:
  - config flow (`config_flow.py`)
  - coordinator behavior (`__init__.py` coordinator class)
  - API client (`custom_components/dewarmte/api/`)
  - manifest metadata (`manifest.json`)
- For any change involving polling, retries, or update frequency, re-check “Fetching data / DataUpdateCoordinator” docs and ensure you’re not increasing load unnecessarily.
- Keep logging helpful and low-noise; never log credentials/tokens.
