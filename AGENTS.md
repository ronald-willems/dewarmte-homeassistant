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
  - `docs/WEBAPP_SCHEMA.md`: what the official web app requires from the settings API (required vs nullable fields, write bodies) — the reference when a user's payload differs from yours.
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

**5. Check what the official client expects**
```bash
python scripts/extract-webapp-schema.py            # required/nullable per field + write bodies
python scripts/extract-webapp-schema.py --dump     # + the raw deserializer
```
The web app at `mydewarmte.com` is a Flutter app, so `main.dart.js` contains the official client's own settings model. The script pulls out which fields it treats as required, which it accepts as null, and what it POSTs to each `settings/*` endpoint, and compares that against our `from_api_response`. Needs no credentials.

- **Use it when** a user reports breakage you cannot reproduce on your own account (e.g. a pump type or capability you don't own). If the official app requires a field, the API must be sending it — otherwise the web app would break for those users too, which is strong evidence against "the API omits this for my setup".
- Findings are written up in `docs/WEBAPP_SCHEMA.md` (with the bundle's sha256/date) and folded into `api/openapi.yaml`. Re-run the script and update both when the hash no longer matches.
- **Never commit `main.dart.js`**: 4.6 MB of minified output, re-minified on every DeWarmte deploy, so symbol names (`u0`, `A.md`, `B.K6`) change and diffs are noise. The script hardcodes none of them — it finds the model by the field names it reads.

**Which values does a settings field accept?** The backend is Django REST Framework, so an authenticated `OPTIONS` on a write endpoint returns the field metadata — including the authoritative list of choices, without writing anything:

```
OPTIONS /v1/customer/products/{deviceId}/settings/cooling/
  -> actions.POST.cooling_control_mode.choices = [scheduled, thermostat, heating_only, cooling_only]
```

Use this before assuming an enum value is valid: these vocabularies change (`manual` was retired around May 2025, `forced` some time after — see the `cooling_control_mode` note in `openapi.yaml`). Only the write endpoints expose `actions`; `OPTIONS` on the read-only `settings/` returns nothing useful.

## When a user reports a bug

Users of this integration run hardware and accounts we cannot see: other pump types, other capabilities, other HA versions, installs updated through HACS rather than from source. That makes reports valuable and unverifiable at the same time. Work them in this order.

- **A report is a hypothesis, not a diagnosis.** Separate what the user *observed* (an error line, an entity stuck at `unknown`) from what they *concluded* ("the API must omit this field for my setup"). The observation is evidence; the conclusion is a guess, however confidently written and however plausible it sounds. Reporters usually have not read the source.
- **Prove the mechanism before changing anything.** You must be able to point at the line in the released code that produces the exact reported symptom. If you cannot explain how that version produces that error, you do not understand the bug yet, and any fix is a guess dressed as a fix. `git show <tag>:<file>` and a diff between the working and broken tags are usually enough to confirm or kill a theory in minutes.
- **Verify they are running the code they think they are.** A reported version number is metadata, not proof of what sits on disk — updates can fail partially, and rollbacks may not restore what the user expects. If a symptom is *impossible* for the source at that tag, suspect the install first and ask for a clean reinstall.
- **Ask for raw evidence, not more opinion.** Request the exact log line and the payload behind it (`custom_components.dewarmte: debug`, then the `Operation settings data:` line), and name the lines you want so the user doesn't have to guess. One payload usually ends the discussion faster than a round of theorising.
- **Use the evidence sources that don't need their hardware.** `scripts/probe-dewarmte-api.py` (does the live API still parse?), `scripts/extract-webapp-schema.py` + `docs/WEBAPP_SCHEMA.md` (what does the official client require?), and `OPTIONS` on a write endpoint (which values are valid?). If the official web app requires a field, the API sends it — that alone refutes most "the API omits X for my setup" theories.
- **Do not write defensive code "just to be safe".** Tolerance for a payload nobody has ever seen is permanent complexity paid for with a guess, and it usually has to stay forever because no one can prove it is unneeded. No evidence, no change.
- **Loud, specific failures are an asset — don't trade them away.** An exception naming the exact field is what makes a report diagnosable at all. Replacing strict access with silent fallbacks converts a precise failure into a vague one and makes the *next* report harder to solve. Prefer making a failure more visible (log level, error text) over making it survivable.
- **Separate the two kinds of fix.** A change justified independently of the report — better logging, a genuinely missing guard — can land immediately. A change that only makes sense if the report's hypothesis is true must wait for evidence. Say which kind you are proposing.
- **Close the loop in public.** If it turns out not to be a bug, say so on the issue with the reasoning and the actual cause. The next person to search that error message should land on the answer, not on an open issue that implies the code is broken.

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
