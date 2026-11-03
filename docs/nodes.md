# Nodes

This page lists every field of a project, node by node, with its symbol and its unit. The
degradation coefficient *Cd* of a heat pump, for instance, is `degradation_coefficient`, and the
shank spacing is in metres. I give only names, symbols and units here; the quantities themselves
are defined in the [GHE Analysis manual](https://www.gheanalysis.com/pages/ghe-analysis-documentation).

A field you have not set is `None`. `p.validate()` tells you which ones a given computation needs.

## Project description

`p.project_description` identifies the project: name, number, client, address and notes. It
travels with the project but no computation reads it, so nothing here can change a result.

`project_name`, `project_no`, `client_name`, `address`, `city`, `prov_state`, `postal_code`,
`country` and `general_notes` are strings; `longitude` and `latitude` are in degrees (they are
kept in case files, not in `.ghe` files).

## Simulation duration

`p.simulation_duration`: 1, 3, 5, 10, 15, 20, 25 or 50 (years).

## Building loads

The loads are the first node where you choose a class, because the way the loads are described
(the application calls it the *Type of thermal load*) changes which columns exist. `p.building_loads` takes one class per type:

| Class | Fields | Unit |
|---|---|---|
| `HourlyBuildingLoadsCombined` | `combined_demand` (8760 values) | kW, heating +, cooling − |
| `HourlyBuildingLoadsSeparate` | `cooling_demand`, `heating_demand`, `dhw_demand` (8760 values each) | kW |
| `HourlyGroundLoadsCombined` | `combined_demand` (8760 values) | kW, heating +, cooling −, applied to the ground |
| `MonthlyBuildingLoadsSeparate` | `cooling_demand`, `heating_demand`, `dhw_demand` (12 values) | kWh |
| | `cooling_peak`, `heating_peak` (12 values) | kW |

With separate demands, the building load is heating − |cooling|. Domestic hot water is served
only in hours whose building load is not zero. The kernel has no calendar and no leap day: hour 0
is the first of the year.

## GSHP system

`p.gshp_system` is the plant between the building and the ground: how many heat pumps, what kind
of system, how much water goes through the field, and the pumps and auxiliary heating around it.

| Field | Symbol | Unit | Meaning |
|---|---|---|---|
| `system_type` | | | `"Water-air (zone)"`, `"Water-water (zone)"`, `"Water-water (loop)"`, `"Water-water (zone) - Geocooling"`, `"Water-water (loop) - Geocooling"` |
| `number_of_heat_pumps` | nHP | HP | ≥ 1 |
| `power_of_auxiliary` | QAux | kW | `ByMode`; per heat pump in a zone system, one unit in a loop system |
| `flow_rate_of_pump_a` | VA | L/min | `ByMode`; the flow through the field |
| `power_of_pump_a` | QA | kW | `ByMode` |
| `flow_rate_of_pump_b` | VB | L/min | `ByMode`; building side. Enters no computation: kept for the project file |
| `power_of_pump_b` | QB | kW | `ByMode` |
| `flow_rate_of_pump_c` | VC | L/min | standing column well: recirculation |
| `power_of_pump_c` | QC | kW | standing column well |

The geocooling variants serve cooling hours through a heat exchanger, without compressor. Pump
powers change no computed temperature or load.

## Heat pump performance

`p.heat_pump_performance` describes one heat pump: what it delivers and at what COP as the
entering fluid temperature changes. How the performance is given (the application's *Input type*) is again a choice of class.

| Field | Symbol | Unit | Meaning |
|---|---|---|---|
| `temperature_limit` | TLim | °C | `ByMode`: lowest entering fluid temperature in heating, highest in cooling, in [−15, 50). The borehole resistances are reported at these temperatures |
| `degradation_coefficient` | Cd | | `ByMode`, in [0, 1]: part-load degradation |
| `dhw_performance` | COPDHW | | `ByMode`: COP of domestic hot water; `math.inf` in cooling (the default) means free recovery of the condenser heat |
| `performance_data` | | | one class per *Input type*, below |

| `performance_data` | Fields | Unit |
|---|---|---|
| `PerformanceConstant` | `cooling_cap`, `cooling_cop`, `heating_cap`, `heating_cop` (numbers) | kW per HP |
| `PerformanceTemperature` | `eft` and `cooling_cap`, `cooling_cop`, `heating_cap`, `heating_cop` (arrays) | °C; kW per HP |
| `ManufacturerData` | `eft`, `tc`, `hr`, `hc`, `he` (arrays) | °C; kW |

In a table, a mode may be left out of a row by giving NaN or 0 for its two values. With
`ManufacturerData` the kernel derives COP = TC / (HR − TC) in cooling and HC / (HC − HE) in
heating.

## Heat carrier fluid

`p.heat_carrier_fluid = ga.HeatCarrierFluid(fluid, antifreeze_mass_concentration)`

`fluid` is one of `"Water"`, `"Ethylene glycol"`, `"Methyl alcohol"`, `"Ethyl alcohol"`,
`"Propylene glycol"` (the tuple `ga.FLUIDS`). `antifreeze_mass_concentration` is in %w, from 0 to
60: write 25 for 25 %w.

## Borehole resistance

Each borehole type is a class with only the fields that type uses, so a single U-loop has no
outer pipe to set. `p.borehole_resistance` takes one of:

| Class | Type |
|---|---|
| `SingleULoop` | single U-loop |
| `DoubleULoopA` | double U-loop, the two U side by side |
| `DoubleULoopD` | double U-loop, the two U crossed |
| `Coaxial` | coaxial |
| `StandingColumn` | standing column well |

| Field | Symbol | Unit | In |
|---|---|---|---|
| `borehole_diameter` | db | m | all |
| `grout_thermal_conductivity` | λg | W/m·K | all |
| `pipe_inner_diameter` | di | m | all (the inner pipe of a coaxial, the dip tube of a well) |
| `pipe_outer_diameter` | do | m | all |
| `pipe_thermal_conductivity` | λp | W/m·K | all |
| `shank_spacing` | s | m | U-loops: centre to centre of the two legs |
| `outer_pipe_inner_diameter` | doi | m | `Coaxial`, `StandingColumn` (the casing) |
| `outer_pipe_outer_diameter` | doo | m | `Coaxial`, `StandingColumn` |
| `outer_pipe_thermal_conductivity` | λo | W/m·K | `Coaxial`, `StandingColumn` |
| `bleed_flow_rate` | Vβ | L/min | `StandingColumn`: at most 30 % of pump C |

The pipe walls and the annulus have to respect the minimum thicknesses that GHE Analysis enforces: 2 mm for
a wall and, for a coaxial, 5 mm of annulus and 0.5 mm between the outer pipe and the borehole
wall. The package warns when they are not met.

## Ground heat exchanger

`p.ground_heat_exchanger` holds the ground, the length of each borehole and where the boreholes
are.

| Field | Symbol | Unit | Meaning |
|---|---|---|---|
| `ground_thermal_conductivity` | λs | W/m·K | |
| `ground_volumetric_capacity` | Cs | MJ/m³·K | |
| `mean_surface_temperature` | T0 | °C | |
| `geothermal_heat_flux` | qg | mW/m² | ≥ 0 |
| `groundwater_flow` | vD | m/s | Darcy velocity; leave unset for no flow |
| `groundwater_flow_direction` | θ | deg. | |
| `active_length` | H | m | of one borehole |
| `burial_depth` | D | m | |
| `coordinates` | | | a `Coordinates` table |

You do not give the undisturbed ground temperature. The kernel computes
Tg = T0 + (D + H/2) qg / λs and returns it with the results.

### Coordinates

`Coordinates` holds the borehole heads: `x` (easting) and `y` (northing) in m, optionally `az`
(direction of inclination, clockwise from north) and `dip` (angle from the horizontal, 90 for a
vertical borehole), both in degrees, and a `label`. From 1 to 625 boreholes; two may not share a
head.

```python
ga.Coordinates.rectangle(nx=4, ny=5, spacing=6.0)              # 20 vertical boreholes
ga.Coordinates.rectangle(nx=2, ny=2, spacing=6.0, origin=(100.0, 50.0))
ga.Coordinates.from_points([(0, 0), (6, 0), (3, 5)], dip=[90, 90, 80], az=[0, 0, 45])
```

Leaving `az` and `dip` unset gives vertical boreholes.

The heads need not follow a grid. A staggered field, an L-shaped lot or a ring of boreholes is a
list of points, and `Coordinates` accepts it as it is:

```python
import numpy as np

angle = np.linspace(0, 2 * np.pi, 8, endpoint=False)
ring = np.column_stack([10 * np.cos(angle), 10 * np.sin(angle)])       # 8 boreholes on a 10 m radius
centre = [(0.0, 0.0)]
ring_field = ga.Coordinates.from_points(np.vstack([ring, centre]))   # assign it to p.ground_heat_exchanger.coordinates
```

[Optimizing the borehole positions](examples/field_layout_optimization.md) lets a search choose
the points.

## Sizing tool

`p.sizing_tool`: `duration_of_yearly_pulse` (ty, years: 1, 3, 5, 10, 15, 20, 25 or 50) and
`duration_of_hourly_peak_pulse` (th, hours: 1 or 6).
