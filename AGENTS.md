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
  - `tests/README.md` (includes optional “real website” scripts using `secrets.yaml`)

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
- **Be careful with “AO/MP/PT/HC” device-type gating**: platforms filter entities based on `device.device_type` and some also check `product_id.startswith(("AO ", "MP ", "PT "))`. Maintain backward compatibility unless you can prove it’s safe.
- **Don’t store secrets**: test scripts may use a local `secrets.yaml`. Never commit credentials; avoid printing secrets to logs.

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

- `tests/README.md` describes optional scripts that hit the real DeWarmte service using a local `secrets.yaml`. These are for manual verification only.

## How to work effectively in this repo (agent guidance)

- Start by identifying the platform(s) affected (`sensor.py`, `climate.py`, etc.) and whether the change touches:
  - config flow (`config_flow.py`)
  - coordinator behavior (`__init__.py` coordinator class)
  - API client (`custom_components/dewarmte/api/`)
  - manifest metadata (`manifest.json`)
- For any change involving polling, retries, or update frequency, re-check “Fetching data / DataUpdateCoordinator” docs and ensure you’re not increasing load unnecessarily.
- Keep logging helpful and low-noise; never log credentials/tokens.

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
  - `tests/README.md` (includes optional “real website” scripts using `secrets.yaml`)

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
- **Be careful with “AO/MP/PT/HC” device-type gating**: platforms filter entities based on `device.device_type` and some also check `product_id.startswith(("AO ", "MP ", "PT "))`. Maintain backward compatibility unless you can prove it’s safe.
- **Don’t store secrets**: test scripts may use a local `secrets.yaml`. Never commit credentials; avoid printing secrets to logs.

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

- `tests/README.md` describes optional scripts that hit the real DeWarmte service using a local `secrets.yaml`. These are for manual verification only.

## How to work effectively in this repo (agent guidance)

- Start by identifying the platform(s) affected (`sensor.py`, `climate.py`, etc.) and whether the change touches:
  - config flow (`config_flow.py`)
  - coordinator behavior (`__init__.py` coordinator class)
  - API client (`custom_components/dewarmte/api/`)
  - manifest metadata (`manifest.json`)
- For any change involving polling, retries, or update frequency, re-check “Fetching data / DataUpdateCoordinator” docs and ensure you’re not increasing load unnecessarily.
- Keep logging helpful and low-noise; never log credentials/tokens.

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
  - `tests/README.md` (includes optional “real website” scripts using `secrets.yaml`)

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
- **Be careful with “AO/MP/PT/HC” device-type gating**: platforms filter entities based on `device.device_type` and some also check `product_id.startswith(("AO ", "MP ", "PT "))`. Maintain backward compatibility unless you can prove it’s safe.
- **Don’t store secrets**: test scripts may use a local `secrets.yaml`. Never commit credentials; avoid printing secrets to logs.

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

- `tests/README.md` describes optional scripts that hit the real DeWarmte service using a local `secrets.yaml`. These are for manual verification only.

## How to work effectively in this repo (agent guidance)

- Start by identifying the platform(s) affected (`sensor.py`, `climate.py`, etc.) and whether the change touches:
  - config flow (`config_flow.py`)
  - coordinator behavior (`__init__.py` coordinator class)
  - API client (`custom_components/dewarmte/api/`)
  - manifest metadata (`manifest.json`)
- For any change involving polling, retries, or update frequency, re-check “Fetching data / DataUpdateCoordinator” docs and ensure you’re not increasing load unnecessarily.
- Keep logging helpful and low-noise; never log credentials/tokens.

