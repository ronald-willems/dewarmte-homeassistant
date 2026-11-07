# What the official DeWarmte web app expects

`mydewarmte.com` is a Flutter app, so its compiled Dart (`main.dart.js`) contains
the official client's own model of the settings API — including which fields it
treats as required and which it accepts as `null`. That is the closest thing to a
spec we have, and it answers questions our own account cannot: our test account
has a single cooling-capable AO pump, so every payload we can observe locally is
the "everything present" case.

This file is a distilled snapshot. **Do not commit `main.dart.js` itself** — it is
4.6 MB of minified output whose symbol names are regenerated on every DeWarmte
deploy, so it would be pure diff noise. Regenerate this snapshot instead:

```bash
python scripts/extract-webapp-schema.py            # report
python scripts/extract-webapp-schema.py --dump     # + raw deserializer
```

## Provenance

| | |
|---|---|
| Source | `https://mydewarmte.com/main.dart.js` |
| Bundle `Last-Modified` | Wed, 29 Jul 2026 06:22:27 GMT |
| Bundle size | 4 644 390 bytes |
| Bundle sha256 | `9c5173f306a141df2d374248ccd9d5bdf4d090c63fc8c85185b34a2daec81a53` |
| Extracted | 2026-08-08 |

If the hash no longer matches what the script reports, the app was redeployed —
re-run the script and update this file.

## Settings model: required vs nullable

One deserializer (`u0` in this build) handles `GET /settings/` **and** the
response of every settings POST, for **all** product types. There is no per-type
variant, and nothing in it is conditioned on the product's `cooling` flag.

The casts throw on a missing or null value:

- enum lookup → `throw "A value must be provided. Supported values: …"`
- `num` / `bool` / `String` casts → TypeError
- only `num?` casts and explicit `x == null ? null : …` checks tolerate null

| Field | Web app | Integration (`from_api_response`) |
|---|---|---|
| `advanced_boost_mode_control` | required bool | required key |
| `advanced_thermostat_delay` | required enum | required key |
| `backup_heating_mode` | required enum | required key |
| `thermostat_type` | required enum | required key |
| `cooling_control_mode` | required enum | required key |
| `cooling_temperature` | required num | required key |
| `cooling_duration` | required num | required key |
| `cooling_schedules` | required list | required key |
| `is_force_cooling_active` | required bool | required key |
| `force_cooling_temperature` | **nullable** num | required key, null ok |
| `force_cooling_end` | **nullable** (explicit null check) | required key, null ok |
| `heat_curve_mode` | required enum | required key |
| `heating_kind` | required enum | required key |
| `heat_curve_s1_outside_temp` | required num | required key |
| `heat_curve_s1_target_temp` | required num | required key |
| `heat_curve_s2_outside_temp` | required num | required key |
| `heat_curve_s2_target_temp` | required num | required key |
| `heat_curve_fixed_temperature` | **nullable** num | required key, null ok |
| `heat_curve_use_smart_correction` | required bool | required key |
| `heating_performance_mode` | required enum | required key |
| `heating_performance_backup_temperature` | required num | required key |
| `sound_mode` | required enum | required key |
| `sound_compressor_power` | required enum | required key |
| `sound_fan_speed` | required enum | required key |
| `warm_water_is_scheduled` | required bool | optional key (we are more lenient) |
| `warm_water_ranges` | required list | optional key (we are more lenient) |
| `legionella_protection_day` | **nullable** num | optional key, null ok |
| `legionella_protection_time` | **nullable** String | optional key, null ok |
| `version` | required num | required key |
| `state` | required enum | required key |

**Our nullability matches theirs exactly.** The five fields the official client
allows to be null are the same five the integration treats as optional. We are
stricter than the app nowhere, and more lenient only on the two warm-water
fields and on the two legionella fields, which we also accept as absent.

The legionella settings are a Pomp T feature: the app's settings menu adds the
"Legionella protection" entry in the same block as "Warm water", only when the
product type is `pt`, and only when the Firebase Remote Config flag
`feature_legionella_enabled` (compiled-in default `true`) is on. AO and MP never
see the screen, although the API returns the fields for them too (an AO returns
`3` / `"00:00"`, a column default). The integration gates its two legionella
entities to PT for that reason (issue #29).

## Write bodies per endpoint

What the app POSTs — compare against `SETTING_GROUPS` in
`custom_components/dewarmte/api/models/settings.py`:

```
settings/heat-curve/            heat_curve_mode, heating_kind,
                                heat_curve_s1_outside_temp, heat_curve_s2_outside_temp,
                                heat_curve_s1_target_temp, heat_curve_s2_target_temp,
                                heat_curve_fixed_temperature, heat_curve_use_smart_correction
settings/heating-performance/   heating_performance_mode, heating_performance_backup_temperature
settings/backup-heating/        backup_heating_mode
settings/sound/                 sound_mode, sound_compressor_power, sound_fan_speed
settings/advanced/              advanced_boost_mode_control, advanced_thermostat_delay
settings/cooling/               thermostat_type, cooling_control_mode, cooling_temperature,
                                cooling_duration, cooling_schedules
settings/warm-water/            warm_water_is_scheduled, warm_water_ranges
settings/legionella/            legionella_protection_day, legionella_protection_time
settings/set-nickname/          nickname
```

The cooling body matches what `_update_settings` sends, including passing
`cooling_schedules` back unchanged.

Forced cooling has its own endpoints, not part of the cooling body:
`settings/cooling/start-forced/` (`force_cool_setpoint`, `forced_duration`) and
`settings/cooling/stop-forced/` (empty body). Both return a full settings object,
parsed with the same deserializer.

## Product model

The products list parser requires `cooling` as a non-null bool on **every**
product, alongside `id`, `name`, `type`, `created_at` (`nickname` and `related_ao`
are nullable). Each product `type` gets its own status parser, but they all share
the one settings model above. We already read this flag into
`Device.supports_cooling`; nothing consumes it yet.

### Status `state` (issue #28)

The products parser picks a status model by `type`. In the bundle extracted
2026-11-07, the models for AO, MP and PT decode a nullable `state` enum, and HC's
model (only `is_on` and the boiler temperatures) does not. Values and the app's
English labels:

| value | label |
|---|---|
| `off` | Off |
| `heating` | Heating |
| `cooling` | Cooling |
| `defrosting` | Defrosting |
| `disinfecting` | Disinfecting |
| `pompt_help` | Tap water heat assist |
| `stand_by` | Standby |
| `unknown` | (empty) |

The app decodes any other value as `unknown` rather than failing. Our Operating
State sensor reports such a value as unknown and logs a warning naming it, so the
list can be extended.

### Settings `state` (issue #30)

The settings model decodes a required `state` enum with the values `applied`,
`sent` and `restored`. The bundle has no reference to the boolean `is_applied`
that the API also returns, so `state` is the field the official client relies
on, and `is_applied` could disappear without breaking the web app. The app's
behaviour around it (bundle of 2026-11-07):

- Every settings write is answered with `state: sent`. The app then shows
  "Saving your changes... This may take a moment." and polls the settings
  endpoint every 3 seconds while the state is still `sent`. It shows the same
  banner on page load when the state is `sent`, so a write from the
  integration is visible there as pending.
- On `applied` it shows "Your changes are saved!".
- On `restored` it reverts the field in the UI and shows "There was a problem
  saving your changes. Please try again later." The backend went back to the
  previous settings version.

The integration publishes the write's echo (`sent`) and sees the outcome on its
next regular poll. The diagnostic "Settings State" sensor exposes the value
(with `version` as an attribute), and the coordinator logs a warning when a
poll turns `sent` into `restored`, so a value that "did not stick" has a trace.

## Settings screens and account capabilities (issue #34)

The bundle of 2026-11-07 (sha256 `b08189517e2a…`) has three settings routes
with no obvious counterpart in the integration: `/settings/heating-preference`,
`/settings/gas-boiler-electric-heating` and `/settings/settings-tado-nox`. They
are redesigns of screens we already cover, not new features:

| Route | Writes | Integration entity |
|---|---|---|
| `/settings/heating-preference` | `settings/heating-performance/` (`heating_performance_mode`, `heating_performance_backup_temperature`) | Heating Performance Mode, Heating Performance Backup Temperature |
| `/settings/gas-boiler-electric-heating` | `settings/backup-heating/` (`backup_heating_mode`) | Backup Heating Mode |
| `/settings/settings-tado-nox` | `smart-control/` (the Pomp T "Smart heating control" page) | not exposed, see `SmartControl` in `openapi.yaml` |

The bundle has exactly one POST site per endpoint and each sends only the
fields listed, so these screens cannot change anything else. `OPTIONS
settings/heating-preference/` returns 404: there is no endpoint of that name.

The screens are gated on **account** flags from `GET /auth/user/` (schema
`UserInfo` in `openapi.yaml`), not on the product:

- `heating_pomp_type`: `AO`, `DWE`, `PT`, `HC`, `MP`, `MPE`
- `backup_heating_device_type`: `ELEMENT`, `GASBOILER`, `NO_BACKUP`
- `has_heating_pomp`, `has_element`, `has_element_connected`, `has_gas_boiler`

The backup heating row is shown when `heating_performance_mode` is not
`pomp_ao_only` and, on an MP, only when `has_element_connected` or
`has_gas_boiler` is true. The backup temperature on the heating preference
screen is hidden on an MP that has neither an element nor a gas boiler. The
screen title follows `backup_heating_device_type`.

We keep gating entities on the product id prefix: the account flags cannot
tell two products on one account apart, and the API accepts the backup fields
for every AO/MP regardless of these flags. Two things to keep in mind:

- The app knows a pump type `MPE`. Our `product_id.startswith("MP ")` gating
  would not match an `MPE ` product id. No user has reported one.
- Our own account reports `has_gas_boiler: true` with
  `backup_heating_device_type: NO_BACKUP`, so the two are not derived from each
  other.

## Why this matters (issue #20)

A user with a Pomp MP without cooling reported that every `number`/`select`
entity went `unknown` after v2.3.2, with a `KeyError` on the cooling thermostat
type field, and proposed that the API omits that field for units without cooling.

This snapshot argues against that: the official web app would break on such a
payload too — `thermostat_type` goes through an enum cast that throws on a
missing value, and the app has no non-cooling code path for the settings screen.
Either the API always sends the full block, or MP owners without cooling cannot
open the settings screen at all.

It also confirms there is nothing to copy from the official client here: its
model is exactly as strict as ours. Any tolerance we add would be tolerance the
official app does not have, i.e. a guess rather than a documented contract. Get
the user's raw `Operation settings data:` payload before changing the parser.
