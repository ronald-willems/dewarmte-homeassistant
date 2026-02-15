# DeWarmte integration – entity reference

## Device abbreviations

| Abbreviation | Device    |
|-------------|-----------|
| AO          | Pomp AO   |
| MP          | Pomp MP   |
| PT          | Pomp T    |
| HC          | Heatcycle |

---

## Sensors

| Name | Description | Devices |
|------|-------------|---------|
| Supply Temperature | Heating supply temperature at the device output. | AO, MP |
| Outdoor Temperature | Outdoor temperature from the sensor connected to the device. | AO, MP |
| Actual Temperature | Current heating circuit temperature. | AO, MP |
| Target Temperature | Target heating temperature set by the heat curve or thermostat. | AO, MP |
| Top Boiler Temperature | Temperature at the top of the boiler (DHW). | PT, HC |
| Bottom Boiler Temperature | Temperature at the bottom of the boiler (DHW). | PT, HC |
| Water Flow | Circulation flow rate for space heating. | AO, MP |
| Heat Input | Heat input power (kW) into the system. | AO, PT, HC, MP |
| Electricity Consumption | Electrical power consumption (kW) of the device. | AO, PT, HC, MP |
| Heat Output | Heat output power (kW) delivered by the device. | AO, PT, HC, MP |
| Electric Backup Usage | Backup electric heating power (kW) for space heating. | AO, MP |
| Fault Code | Current fault or error code reported by the device. | AO, PT, HC, MP |
| Heat Input Energy | Energy (kWh) integrated from the Heat Input power sensor. | AO, PT, HC, MP |
| Electricity Consumption Energy | Energy (kWh) integrated from the Electricity Consumption power sensor. | AO, PT, HC, MP |
| Heat Output Energy | Energy (kWh) integrated from the Heat Output power sensor. | AO, PT, HC, MP |
| Electric Backup Usage Energy | Energy (kWh) integrated from the Electric Backup Usage power sensor. | AO, MP |
| CoP | Coefficient of performance: heat output energy divided by electricity input energy. | AO, PT, HC, MP |
| Gas Boiler | Whether the gas boiler backup heating is active. | AO, MP |
| Thermostat | Whether the space heating thermostat is calling for heat. | AO, MP |
| Is On | Whether the device is currently running. | AO, PT, MP |
| Is Connected | Whether the device is connected and reachable. | AO, PT, MP |

---

## Controls

| Name | Description | Devices |
|------|-------------|---------|
| Warm Water | Climate entity for warm water target temperature and schedule (eco, comfort, boost, away). | PT, HC |
| Heat Curve S1 Outside Temperature | First heat curve point: outside temperature (℃). | AO, MP |
| Heat Curve S1 Target Temperature | First heat curve point: target supply temperature (℃). | AO, MP |
| Heat Curve S2 Outside Temperature | Second heat curve point: outside temperature (℃). | AO, MP |
| Heat Curve S2 Target Temperature | Second heat curve point: target supply temperature (℃). | AO, MP |
| Heat Curve Fixed Temperature | Fixed supply temperature when heat curve mode is fixed. | AO, MP |
| Heating Performance Backup Temperature | Outdoor temperature below which backup heating is allowed. | AO, MP |
| Cooling Temperature | Target temperature for cooling mode (when cooling is supported). | AO, MP |
| Cooling Duration | Maximum duration (seconds) for a cooling run (when cooling is supported). | AO, MP |
| Warm Water Target Temperature | Target temperature for domestic hot water. | PT |
| Heat Curve Mode | Whether the heat curve uses weather compensation or a fixed temperature. | AO, MP |
| Heating Kind | Type of heating system: custom, floor, radiator, or both. | AO, MP |
| Heating Performance Mode | How heat pump and backup work together: auto, heat pump only, heat pump and backup, or backup only. | AO, MP |
| Sound Mode | Overall sound profile: normal or silent. | AO, MP |
| Sound Compressor Power | Compressor power level for sound tuning: min, med, or max. | AO, MP |
| Sound Fan Speed | Fan speed level for sound tuning: min, med, or max. | AO, MP |
| Advanced Thermostat Delay | Delay before reacting to thermostat demand: min, med, or max. | AO, MP |
| Backup Heating Mode | Backup heating behaviour: auto, eco, or comfort. | AO, MP |
| Cooling Thermostat Type | Whether the thermostat is heating-only or heating and cooling (when cooling is supported). | AO, MP |
| Cooling Control Mode | Cooling control: thermostat, cooling only, heating only, or forced (when cooling is supported). | AO, MP |
| Boost Mode | Switch to temporarily enable boost mode for space heating. | AO, MP |
