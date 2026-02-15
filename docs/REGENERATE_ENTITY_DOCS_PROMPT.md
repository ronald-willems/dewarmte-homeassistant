# Regenerate entity documentation

Regenerate the DeWarmte integration entity reference document.

**Output file:** `docs/ENTITIES.md`

**Steps:**

1. **Read the source code** for entity names, one-sentence descriptions, and device applicability:
   - `custom_components/dewarmte/sensor.py` — `SENSOR_DESCRIPTIONS`, integration energy sensors (from power sensors), and CoP sensor
   - `custom_components/dewarmte/binary_sensor.py` — `BINARY_SENSOR_DESCRIPTIONS`
   - `custom_components/dewarmte/select.py` — `MODE_SELECTS` (applies to AO and MP only)
   - `custom_components/dewarmte/switch.py` — `SWITCH_DESCRIPTIONS`
   - `custom_components/dewarmte/number.py` — `NUMBER_DESCRIPTIONS`
   - `custom_components/dewarmte/climate.py` — `CLIMATE_DESCRIPTIONS`

2. **Document structure for `docs/ENTITIES.md`:**
   - **Title:** e.g. "DeWarmte integration – entity reference"
   - **Legend:** Device abbreviations — AO = Pomp AO, MP = Pomp MP, PT = Pomp T, HC = Heatcycle
   - **Sensors table** with columns: **Name** | **Description** (one sentence) | **Devices** (abbreviations only, e.g. AO, MP, PT, HC)
   - **Controls table** with columns: **Name** | **Description** (one sentence) | **Devices** (abbreviations only)

3. **Logical ordering (do not sort alphabetically):**
   - **Sensors:** Group by theme — temperature sensors (Supply, Outdoor, Actual, Target, Top Boiler, Bottom Boiler); Water Flow; power sensors (Heat Input, Electricity Consumption, Heat Output, Electric Backup Usage); Fault Code; integration energy sensors (kWh from power sensors); CoP; binary sensors (Gas Boiler, Thermostat, Is On, Is Connected).
   - **Controls:** Group by type and function — Climate (Warm Water); Numbers (heat curve S1/S2, fixed temp, backup temp; cooling temp/duration; warm water target); Selects (heat curve mode, heating kind, heating performance mode; sound mode, compressor power, fan speed; thermostat delay; backup heating mode; cooling thermostat type, cooling control mode); Switches (Boost Mode).

4. **Rules:**
   - Descriptions: exactly one sentence per entity.
   - Devices column: use only abbreviations (e.g. "AO, MP" or "AO, PT, HC, MP").
   - Cooling-related controls (cooling temperature, duration, thermostat type, control mode) apply to AO, MP when the device supports cooling; still list them with device abbreviations AO, MP.

Overwrite `docs/ENTITIES.md` with the regenerated content.
