# Computations

A computation is a method call on a project. The package checks that the project is complete,
writes it as a case, has the executable compute it, and reads the answer into a result object.
Its attributes are named after the quantities they hold, with the units the application displays.
[Methods](methods.md) describes the methods behind each call.

The GHE module computes seven things:

| Method | Computes | Returns |
|---|---|---|
| `ga.fluid_properties(fluid, temperatures)` | properties of the heat carrier fluid | `FluidProperties` |
| `p.compute_borehole_resistance()` | borehole resistances at the two temperature limits | `BoreholeResistanceResult` |
| `p.compute_gfunction()` | thermal response of the field | `GFunctionResult` |
| `p.simulate()` | hourly simulation, field coupled to the heat pumps | `SimulationResult` |
| `p.size()` | total borehole length, three-pulse method | `SizingResult` |
| `p.compute_thermal_plume_2d(time)` | 2D thermal plume | `ThermalPlume2DResult` |
| `p.compute_thermal_plume_3d(time)` | 3D thermal plume | `ThermalPlume3DResult` |

They all accept the keyword arguments `threads=None`, `timeout=None`, `keep_files=False` and
`strict=False` ([Many cases](many-cases.md) for threads, [Errors](errors.md) for `strict`).

The names follow those of the application's Borehole designer, Sizing tool and console, so a
result can be set beside what it displays. A quantity given in heating and in cooling is a `ByMode`, as it is for inputs.

## Every result

Each result records whether the computation converged and how it was obtained.

| Attribute | Content |
|---|---|
| `status`, `converged` | `"ok"` or `"notConverged"`; `True` or `False` |
| `warnings` | the kernel's warnings, as a list of strings (also raised as `KernelWarning`) |
| `meta` | program version, interface version, command, thread count |
| `case` | the exact case that was sent, as a `dict` |
| `raw` | the executable's output, with its own names and units |
| `save(path)` | writes case and output together; `ga.load_result(path)` reads them back |

## Simulation

The kernel couples the borehole field to the heat pumps hour by hour over the whole duration. The
loads set the heat flow and the ground responds through the g-function. The entering fluid
temperature in turn changes the heat pumps' COP and capacity, which changes the load on the
ground, so the kernel iterates until the two sides agree.

```python
result = p.simulate()
```

What comes back:

| Attribute | Content |
|---|---|
| `eft` | entering fluid temperature, °C, one value per hour (shortcut for `hourly.entering_fluid_temperature`) |
| `hourly` | the requested series, as numpy arrays |
| `daily_eft`, `monthly_eft` | mean entering fluid temperature of each day (years × 365 values) and of each month (years × 12), °C |
| `summary` | `minimum_eft`, `maximum_eft`, `hours_below/above_temperature_limit`, `hours_below/above_r_cop_range`, `peak_heat_pump_load`, `peak_ground_load` (W/m) |
| `undisturbed_ground_temperature` | Tg, °C |
| `borehole_resistance` | as in [Borehole resistance](#borehole-resistance) |
| `heat_pumps` | `cop_at_tlim`, `total_installed_capacity_at_tlim` |
| `iterations`, `residuals` | iterations used; last change of the EFT (K) and of the ground load (kW) |
| `gfunction_converged` | whether the g-function met its criterion |
| `gfunction` | the g-function values (mK/W), with `p.simulate(include_gfunction=True)` only |

Heat flows are signed from the ground's point of view: a ground load is positive when heat is
injected into the ground. The application's charts use the same sign.

### Series

Twenty hourly series are available. By default a simulation returns two, the entering fluid
temperature and the effective COP, about 5 MB for 25 years. `series="all"` returns the twenty; a
list returns the ones it names.

```python
result = p.simulate(series=["entering_fluid_temperature", "heat_pump_load", "ground_load"])
print(result.hourly.heat_pump_load.shape)
```

| Series | | | |
|---|---|---|---|
| `entering_fluid_temperature` | `leaving_fluid_temperature` | `fluid_temperature_difference` | `ground_load` |
| `building_load` | `dhw_load` | `heat_pump_load` | `auxiliary_load` |
| `dhw_covered` | `cop` | `effective_cop` | `effective_capacity` |
| `heat_pumps_full_load` | `heat_pumps_part_load` | `heat_pumps_off` | `equivalent_heat_pumps` |
| `part_load_ratio` | `part_load_factor` | `effective_borehole_resistance` | `fluid_resistance` |

They are listed in `ga.SERIES`; `ga.DEFAULT_SERIES` is the default pair. If you read a series you
did not request, you get a `SeriesNotRequested` error that says what to call, not an empty
array:

```python
result = p.simulate()
try:
    result.hourly.leaving_fluid_temperature
except ga.SeriesNotRequested as error:
    print(error)
```

```text
the series 'leaving_fluid_temperature' was not computed; run p.simulate(series=[..., 'leaving_fluid_temperature']) or p.simulate(series='all')
```

Hours without a building load carry NaN in `cop`, `effective_cop` and `effective_capacity`. The
heat pumps do not run in those hours, so there is no COP to report; the package keeps the NaN and
does not warn.

### As a table

With pandas installed, `to_dataframe()` returns the series indexed by the integer hour, with the
columns `year` and `day`:

```python
table = result.to_dataframe()
print(table.groupby("year").entering_fluid_temperature.min().head(3))
```

## Sizing

Given the loads, the Sizing tool returns the total borehole length each mode requires. It uses the
three-pulse method: a yearly pulse, a monthly pulse and an hourly peak.

```python
sizing = p.size()
print(sizing.total_borehole_length.heating, sizing.total_borehole_length.cooling)
```

The Sizing tool's outputs, each a `ByMode`: `yearly_ground_load` (qy), `monthly_ground_load`
(qm), `hourly_ground_load` (qh) in kW; `yearly_response_factor` (Rgy), `monthly_response_factor`
(Rgm), `hourly_peak_response_factor` (Rgh) and `effective_borehole_resistance` (Rb*) in mK/W;
`dt` (dT, K); `total_borehole_length` (L) and `active_length` (H) in m;
`mean_fluid_temperature` (Tm) and `undisturbed_ground_temperature` (Tg) in °C; and `heat_pumps`.
`governing_mode` is the mode that needs the longer field, and `governing_total_borehole_length`
its length. The sizing loads are positive when heat is extracted, the opposite of the simulation; the
application's sizing panel shows the same sign.

These satisfy the sizing equation, L = (qy·Rgy + qm·Rgm + qh·Rgh + qh·Rb*) / (Tg − Tm).

The Sizing tool, unlike the simulation, does not report whether it converged. The package checks
that every length it returns is finite.

## Borehole resistance

These are the results of the Borehole designer: the thermal resistance between the fluid and the
borehole wall, for the borehole type, fluid and flow you set, at each of the two temperature
limits. The call needs no loads and no heat pump table, so it is the quickest way to compare
grouts or pipes.

```python
rb = p.compute_borehole_resistance()
print(rb.effective_borehole_resistance)
```

The Borehole designer's results, each a `ByMode` (heating at the heating limit, cooling at the
cooling limit): `temperature_limit`, `flow_rate_per_borehole` (L/min), `convective_resistance`
(Rf), `internal_borehole_resistance` (Ra), `equivalent_borehole_resistance` (Rb),
`effective_borehole_resistance` (Rb*) in mK/W and `borehole_efficiency` (χ, %).
`pipe_resistance` (Rp) is a single value. With `include_grid=True`, `grid` holds the tables
before interpolation, as numpy arrays.

## g-function

The g-function is the response of the field to a constant heat rate. The simulation is built on
it, and you can also use it on its own to apply other loads to the ground.

```python
gf = p.compute_gfunction()
print(gf.time.shape, gf.values[:3])
```

`time` (s) and `values` (mK/W, per unit heat rate per metre of total borehole length), numpy
arrays; `dimensionless` is 2π·λs·values. `gfunction_converged` says whether the criterion was met.

## Fluid properties

Density, specific heat, conductivity and viscosity of a heat carrier fluid at the temperatures
you choose. The call needs a fluid, not a project:

```python
fluid = ga.HeatCarrierFluid("Propylene glycol", antifreeze_mass_concentration=25)
properties = ga.fluid_properties(fluid, [-5, 0, 5])
print(properties.freezing_temperature, properties.density)
```

`temperature`, `density`, `specific_heat_capacity`, `thermal_conductivity` and `viscosity` at the
requested temperatures (numpy arrays), and `freezing_temperature` in °C.

## Thermal plumes

This is the thermal plume the application draws in its *Ground heat exchanger* panel, computed at
`time` hours since commissioning on the same grid. The simulation runs first and its hourly ground
load is superposed on the g-function of each borehole.

```python
plume = p.compute_thermal_plume_2d(8760)
print(plume.x.shape, plume.y.shape, plume.values.shape)      # values[iy, ix]
```

`reading` selects what is returned: `"Temp. perturbation"` (the default, ΔT in K) or
`"Ground Temp."` (°C, the undisturbed temperature plus ΔT).

```python
plume3d = p.compute_thermal_plume_3d(8760, reading="Ground Temp.")
print(plume3d.values.shape)                                  # values[iz, iy, ix], z = depth
```

- 2D is the plane at mid-length, by infinite moving line sources over a 300 m window around each
  borehole. Inclined boreholes are taken at their midpoint.
- 3D uses moving finite line sources with the buried depth, for vertical boreholes only. Its grid
  is fitted to the region the smallest contour reaches: `contour_min`, `contour_max` and
  `num_of_contours` are the contour settings of the plume, in the terms of the reading (by default, ten levels
  of ΔT from 0.1 to 1.0 K).
