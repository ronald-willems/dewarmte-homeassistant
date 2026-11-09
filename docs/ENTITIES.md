# DeWarmte integration – entity reference

## Device abbreviations

| Abbreviation | Device    |
|-------------|-----------|
| AO          | Pomp AO   |
| MP          | Pomp MP   |
| PT          | Pomp T    |
| HC          | Heatcycle |

"(cooling)" means the entity is only created when DeWarmte reports that the device supports cooling.

---

## Sensors

| Name | Description | Devices |
|------|-------------|---------|
| Supply Temperature | Heating supply temperature at the device output. | AO, MP |
| Outdoor Temperature | Outdoor temperature from the sensor connected to the device. | AO, MP |
| Actual Temperature | Current heating circuit temperature. | AO, MP |
| Target Temperature | Target heating temperature set by the heat curve or thermostat. | AO, MP |
| Top Boiler Temperature | Temperature at the top of the hot water tank. | PT, HC |
| Bottom Boiler Temperature | Temperature at the bottom of the hot water tank. | PT, HC |
| Water Flow | Circulation flow rate for space heating (L/min). | AO, MP |
| Heat Input | Heat input power (kW) into the system. | AO, MP, PT, HC |
| Electricity Consumption | Electrical power consumption (kW) of the device. | AO, MP, PT, HC |
| Heat Output | Heat output power (kW) delivered by the device. | AO, MP, PT, HC |
| Electric Backup Usage | Backup electric heating power (kW) for space heating. | AO, MP |
| Fault Code | Current fault or error code reported by the device. | AO, MP, HC |
| Operating State | What the device is doing right now: off, heating, cooling, defrosting, disinfecting, tap water heat assist, standby or unknown. | AO, MP, PT |
| Settings State | Diagnostic sensor showing whether the latest settings change was sent, applied by the pump, or restored by DeWarmte, with the settings version as an attribute. | AO, MP, PT |
| Forced Cooling Setpoint | Target temperature of the current forced-cooling run. | AO, MP (cooling) |
| Forced Cooling End | Time at which the current forced-cooling run ends. | AO, MP (cooling) |
| Heat Input Energy | Energy (kWh) integrated from the Heat Input power sensor since the integration was installed. | AO, MP, PT, HC |
| Electricity Consumption Energy | Energy (kWh) integrated from the Electricity Consumption power sensor since the integration was installed. | AO, MP, PT, HC |
| Heat Output Energy | Energy (kWh) integrated from the Heat Output power sensor since the integration was installed. | AO, MP, PT, HC |
| Electric Backup Usage Energy | Energy (kWh) integrated from the Electric Backup Usage power sensor since the integration was installed. | AO, MP |
| Electric Backup Energy | Year-to-date energy (kWh) of the electric backup element, from the insights the official app shows. Polled every 15 minutes; resets on 1 January. | MP, PT |
| CoP | Coefficient of performance: Heat Output Energy divided by Electricity Consumption Energy, so a running average since the integration was installed. | AO, MP, PT, HC |
| Gas Boiler | Whether the gas boiler backup heating is active. | AO, MP |
| Thermostat | Whether the space heating thermostat is calling for heat. | AO, MP |
| Is On | Whether the device is currently running. | AO, MP, PT |
| Is Connected | Whether the device is connected and reachable. | AO, MP, PT |
| Electric Backup | Whether the electric backup element is on: the space-heating element on an MP (from tb-status), the hot water tank heater on a PT (from its status). | MP, PT |
| Forced Cooling Active | Whether a forced-cooling run is in progress. | AO, MP (cooling) |

---

## Controls

| Name | Description | Devices |
|------|-------------|---------|
| Heat Curve S1 Outside Temperature | First heat curve point: outside temperature (℃). | AO, MP |
| Heat Curve S1 Target Temperature | First heat curve point: target supply temperature (℃). | AO, MP |
| Heat Curve S2 Outside Temperature | Second heat curve point: outside temperature (℃). | AO, MP |
| Heat Curve S2 Target Temperature | Second heat curve point: target supply temperature (℃). | AO, MP |
| Heat Curve Fixed Temperature | Fixed supply temperature when heat curve mode is fixed. | AO, MP |
| Heating Performance Backup Temperature | Outdoor temperature below which backup heating is allowed. | AO, MP |
| Cooling Temperature | Target temperature for cooling mode. | AO, MP (cooling) |
| Cooling Duration | Maximum duration (seconds) of a cooling run. | AO, MP (cooling) |
| Warm Water Target Temperature | Fixed target temperature for domestic hot water (40–70 ℃ in steps of 5). | PT |
| Smart Control Minimum Temperature | Lowest warm water setpoint smart heating control may use (40–70 ℃); only used while smart heating control is on. | PT |
| Smart Control Maximum Temperature | Highest warm water setpoint smart heating control may use (40–70 ℃); only used while smart heating control is on. | PT |
| Heat Curve Mode | Whether the heat curve uses weather compensation or a fixed temperature. | AO, MP |
| Heating Kind | Type of heating system: custom, floor, radiator, or both. | AO, MP |
| Heating Performance Mode | How heat pump and backup work together: auto, heat pump only, heat pump and backup, or backup only. | AO, MP |
| Sound Mode | Overall sound profile: normal or silent. | AO, MP |
| Sound Compressor Power | Compressor power level for sound tuning: min, med, or max. | AO, MP |
| Sound Fan Speed | Fan speed level for sound tuning: min, med, or max. | AO, MP |
| Advanced Thermostat Delay | Delay before reacting to thermostat demand: min, med, or max. | AO, MP |
| Backup Heating Mode | Backup heating behaviour: auto, eco, or comfort. | AO, MP |
| Cooling Thermostat Type | Whether the thermostat is heating-only or heating and cooling. | AO, MP (cooling) |
| Cooling Control Mode | Cooling control: scheduled, thermostat, cooling only, or heating only. | AO, MP (cooling) |
| Legionella Protection Day | Weekday (monday–sunday) of the weekly legionella protection run, which heats the tank to 60 ℃ for 20 minutes. | PT |
| Legionella Protection Time | Start time of the weekly legionella protection run. | PT |
| Boost Mode | Switch to temporarily enable boost mode for space heating. | AO, MP |
| Smart Heating Control | Switch to turn smart heating control (dynamic tariffs / solar, via NOX Energy) on or off; requires the smart heating control terms to be accepted in the DeWarmte app. | PT |

Schedules (the warm water schedule of the Pomp T and the cooling schedules of the Pomp AO/MP) are not exposed; manage them in the DeWarmte app.

---

## Services

| Service | Parameters | Devices |
|---------|------------|---------|
| `dewarmte.start_forced_cooling` | `device_id`, `setpoint` (10–25 ℃), `duration_hours` (1–72): start cooling now for a fixed duration, overriding the other cooling settings until it ends. | AO, MP (cooling) |
| `dewarmte.stop_forced_cooling` | `device_id`: stop a running forced-cooling run. | AO, MP (cooling) |

---

## Energy history statistics

With the energy history import switched on, the integration writes DeWarmte's own hourly energy history as long-term statistics named *Heat supplied*, *Electricity consumed* and *Electric backup usage* per device, under the `dewarmte:` namespace. These are not entities: they appear in the Energy dashboard and in statistics cards, but cannot be used in automations or Utility Meter helpers. In the Energy dashboard, use either these statistics or the energy sensors above for the same device, not both.
