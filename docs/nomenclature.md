# Nomenclature

The symbols follow the notation of the literature the kernel comes from ([Methods](methods.md)).
GHE Analysis uses the same ones, and its
[manual](https://www.gheanalysis.com/pages/ghe-analysis-documentation) defines each quantity. The
units are the SI units the application displays; flow rates, for instance, are in L/min.

## Ground and field

| Symbol | Quantity | Unit | Attribute |
|---|---|---|---|
| λs | ground thermal conductivity | W/m·K | `ground_thermal_conductivity` |
| Cs | ground volumetric heat capacity | MJ/m³·K | `ground_volumetric_capacity` |
| T0 | mean surface temperature | °C | `mean_surface_temperature` |
| qg | geothermal heat flux | mW/m² | `geothermal_heat_flux` |
| Tg | undisturbed ground temperature, Tg = T0 + (D + H/2) qg / λs | °C | `undisturbed_ground_temperature` (result) |
| vD | Darcy velocity of groundwater | m/s | `groundwater_flow` |
| θ | direction of groundwater flow | deg. | `groundwater_flow_direction` |
| H | active length of one borehole | m | `active_length` |
| D | burial depth | m | `burial_depth` |
| L | total borehole length of the field | m | `total_borehole_length` (sizing) |
| az, dip | azimuth and dip of a borehole (90 = vertical) | deg. | `Coordinates` |

## Borehole

| Symbol | Quantity | Unit | Attribute |
|---|---|---|---|
| db | borehole diameter | m | `borehole_diameter` |
| λg | grout thermal conductivity | W/m·K | `grout_thermal_conductivity` |
| di, do | inner and outer diameter of the pipe | m | `pipe_inner_diameter`, `pipe_outer_diameter` |
| λp | pipe thermal conductivity | W/m·K | `pipe_thermal_conductivity` |
| s | shank spacing, centre to centre | m | `shank_spacing` |
| doi, doo | inner and outer diameter of the outer pipe or casing | m | `outer_pipe_inner_diameter`, `outer_pipe_outer_diameter` |
| λo | thermal conductivity of the outer pipe | W/m·K | `outer_pipe_thermal_conductivity` |
| Vβ | bleed flow rate of a standing column well | L/min | `bleed_flow_rate` |
| Rf | convective resistance | m·K/W | `convective_resistance` |
| Rp | pipe resistance | m·K/W | `pipe_resistance` |
| Rb | local (equivalent) borehole resistance | m·K/W | `equivalent_borehole_resistance` |
| Ra | internal borehole resistance | m·K/W | `internal_borehole_resistance` |
| Rb\* | effective borehole resistance | m·K/W | `effective_borehole_resistance` |
| χ | borehole efficiency | % | `borehole_efficiency` |

## System and heat pumps

| Symbol | Quantity | Unit | Attribute |
|---|---|---|---|
| nHP | number of heat pumps | – | `number_of_heat_pumps` |
| VA, VB, VC | flow rates of pumps A (field), B (building) and C (well recirculation) | L/min | `flow_rate_of_pump_a`, … |
| QA, QB, QC | powers of pumps A, B and C | kW | `power_of_pump_a`, … |
| QAux | power of the auxiliary heating or cooling | kW | `power_of_auxiliary` |
| TLim | temperature limit of the heat pumps | °C | `temperature_limit` |
| EFT | entering fluid temperature, at the heat pump inlet | °C | `eft` (result) |
| COP | coefficient of performance | – | `cop` (series) |
| COPDHW | COP of domestic hot water | – | `dhw_performance` |
| Cd | part-load degradation coefficient | – | `degradation_coefficient` |
| PLR | part-load ratio | – | `part_load_ratio` (series) |
| PLF | part-load factor, PLF = 1 − Cd (1 − PLR) | – | `part_load_factor` (series) |

## Sizing tool

| Symbol | Quantity | Unit | Attribute |
|---|---|---|---|
| ty | duration of the yearly pulse | years | `duration_of_yearly_pulse` |
| th | duration of the hourly peak pulse | hours | `duration_of_hourly_peak_pulse` |
| qy, qm, qh | yearly, monthly and hourly ground loads | kW | `yearly_ground_load`, … |
| Rgy, Rgm, Rgh | response factors of the three pulses | m·K/W | `yearly_response_factor`, … |
| Tm | mean fluid temperature | °C | `mean_fluid_temperature` |
| dT | temperature difference across the field | K | `dt` |

The total length satisfies L = (qy·Rgy + qm·Rgm + qh·Rgh + qh·Rb\*) / (Tg − Tm).

## Signs

- In a combined load, heating is positive and cooling negative. Separate demands are magnitudes.
- In a simulation, a ground load is positive when heat is injected into the ground.
- In the sizing, the ground loads are positive when heat is extracted, which is also the sign the
  application shows.
