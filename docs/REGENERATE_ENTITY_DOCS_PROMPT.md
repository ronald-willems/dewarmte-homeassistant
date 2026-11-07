# Regenerate entity documentation

Regenerate the DeWarmte integration entity reference document.

**Output file:** `docs/ENTITIES.md`

**Steps:**

1. **Read the source code** for entity names, one-sentence descriptions and device applicability. Only the platforms listed in `PLATFORMS` in `custom_components/dewarmte/__init__.py` are loaded; do not document a platform file that is not in that list (`climate.py` is not).
   - `custom_components/dewarmte/sensor.py` — `SENSOR_DESCRIPTIONS`, the energy integration sensors (one per power sensor) and the CoP sensor
   - `custom_components/dewarmte/binary_sensor.py` — `BINARY_SENSOR_DESCRIPTIONS`
   - `custom_components/dewarmte/number.py` — `NUMBER_DESCRIPTIONS`
   - `custom_components/dewarmte/select.py` — `MODE_SELECTS`
   - `custom_components/dewarmte/time.py` — `TIME_DESCRIPTIONS`
   - `custom_components/dewarmte/switch.py` — `SWITCH_DESCRIPTIONS`
   - `custom_components/dewarmte/services.yaml` — the services
   - Device applicability is the description's `device_types`; `requires_cooling=True` means "only when the device supports cooling".

2. **Document structure for `docs/ENTITIES.md`:**
   - **Title:** "DeWarmte integration – entity reference"
   - **Legend:** device abbreviations — AO = Pomp AO, MP = Pomp MP, PT = Pomp T, HC = Heatcycle
   - **Sensors table**: **Name** | **Description** (one sentence) | **Devices**
   - **Controls table**: **Name** | **Description** (one sentence) | **Devices**
   - **Services** list: name, parameters, which devices
   - **Energy history statistics**: the imported `dewarmte:` statistics are not entities; name them and say so.

3. **Logical ordering (do not sort alphabetically):**
   - **Sensors:** temperatures (Supply, Outdoor, Actual, Target, Top Boiler, Bottom Boiler); Water Flow; power (Heat Input, Electricity Consumption, Heat Output, Electric Backup Usage); Fault Code; state sensors (Operating State, Settings State); forced cooling (Setpoint, End); energy sensors (kWh from the power sensors); CoP; binary sensors (Gas Boiler, Thermostat, Is On, Is Connected, Electric Backup, Forced Cooling Active).
   - **Controls:** numbers (heat curve S1/S2, fixed temperature, backup temperature; cooling temperature and duration; warm water target; smart control minimum and maximum); selects (heat curve mode, heating kind, heating performance mode; sound mode, compressor power, fan speed; thermostat delay; backup heating mode; cooling thermostat type, cooling control mode; legionella protection day); time (legionella protection time); switches (Boost Mode, Smart Heating Control).

4. **Rules:**
   - Exactly one sentence per entity.
   - Devices column: abbreviations only, e.g. "AO, MP" or "AO, MP, PT, HC".
   - Cooling-related entities apply to AO and MP only when the device supports cooling; list them as "AO, MP (cooling)".
   - Mention a requirement in the description when the code or the app has one (smart heating control terms, cooling support).

Overwrite `docs/ENTITIES.md` with the regenerated content.
