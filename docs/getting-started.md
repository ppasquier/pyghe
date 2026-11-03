# Getting started

On this page I build a small project from nothing, simulate it for 25 years, size it, and save it
as a `.ghe` file. The package must be installed and the executable found
([Installation](install.md)).

## Describing a project

A `Project` is a tree of nodes: the building loads, the heat pump system and its performance, the
heat carrier fluid, the borehole and the ground heat exchanger, which holds the ground and the
field. Each node is an attribute of the project, and I fill them in one after the other. Start
with the loads. The kernel wants one value per hour for a year, so 8760 values. The building below
is invented: it heats in winter and cools a little in summer.

```python
import numpy as np
import pyghe as ga

# Separate demands in kW, one value per hour; the cooling demand is taken in absolute value.
hours = np.arange(8760)
winter = np.cos(2 * np.pi * hours / 8760)
heating = 40 * np.clip(winter, 0, None) + 4 * (hours % 24 > 6) * (winter > 0)
cooling = 20 * np.clip(-winter, 0, None)
```

Now the project itself. The simulation length belongs to the project as a whole, not to a node.
The loads are an object of the class that matches the type of thermal load; here, hourly demands
with heating and cooling given separately:

```python
p = ga.Project()
p.simulation_duration = 25                                   # years

p.building_loads = ga.HourlyBuildingLoadsSeparate(
    cooling_demand=cooling, heating_demand=heating, dhw_demand=np.zeros(8760))
```

Next, the ground-source heat pump (GSHP) system. Anything that has one value for heating and
another for cooling is a `ByMode`. The flow rate is the one through the borehole field, in litres
per minute:

```python
p.gshp_system.system_type = "Water-water (zone)"
p.gshp_system.number_of_heat_pumps = 4
p.gshp_system.flow_rate_of_pump_a = ga.ByMode(heating=240, cooling=240)     # L/min
```

Then the heat pumps. The temperature limits are the entering fluid temperatures within which they
may work: at least 0 °C when heating, at most 30 °C when cooling. The performance is a small table
in entering fluid temperature, for one heat pump:

```python
p.heat_pump_performance.temperature_limit = ga.ByMode(heating=0.0, cooling=30.0)   # °C
p.heat_pump_performance.performance_data = ga.PerformanceTemperature(
    eft=[-5, 30],
    cooling_cap=[25, 20], cooling_cop=[6, 3.5],
    heating_cap=[15, 24], heating_cop=[3, 5])                # kW per heat pump

p.heat_carrier_fluid = ga.HeatCarrierFluid("Propylene glycol", antifreeze_mass_concentration=25)
```

The antifreeze concentration is a mass percentage: 25 means 25 %w, not 0.25.

The borehole. Each type of borehole is its own class, so you cannot set a field it does not
have:

```python
p.borehole_resistance = ga.SingleULoop(
    borehole_diameter=0.152, grout_thermal_conductivity=1.25, shank_spacing=0.1,
    pipe_inner_diameter=0.033, pipe_outer_diameter=0.044, pipe_thermal_conductivity=0.39)
```

And the ground, with a field of nine boreholes on a 6 m square grid:

```python
g = p.ground_heat_exchanger
g.ground_thermal_conductivity = 2.5                          # W/m·K
g.ground_volumetric_capacity = 2.2                           # MJ/m³·K
g.mean_surface_temperature = 10.0                            # °C
g.geothermal_heat_flux = 60                                  # mW/m²
g.active_length = 150                                        # m
g.burial_depth = 2                                           # m
g.coordinates = ga.Coordinates.rectangle(nx=3, ny=3, spacing=6.0)

p.sizing_tool.duration_of_yearly_pulse = 10                  # years
p.sizing_tool.duration_of_hourly_peak_pulse = 6              # hours
```

The undisturbed ground temperature is not an input. The kernel works it out from the surface
temperature, the heat flux, the conductivity and the depths, and returns it with the results.

`validate` lists what the project still lacks for a given computation, without raising an error:

```python
assert p.validate("simulate") == []
```

## Simulating

```python
result = p.simulate()
print(result)
```

```text
<SimulationResult ghe simulation: ok>
  iterations = 5, residuals: EFT 0.000341 K, ground load 0.00117 kW
  undisturbed_ground_temperature (Tg) = 11.848 °C
  hourly: effective_cop, entering_fluid_temperature
  minimum_eft = 3.7409949614301645 °C
  maximum_eft = 17.164371538184362 °C
  hours_below_temperature_limit = 0 h
  ...
```

The simulation converged in five iterations; the residuals are the last changes of the entering
fluid temperature and of the ground load. No hour falls below the heating limit of 0 °C, so the
heat pumps stayed within their range.

The entering fluid temperature itself, hour by hour for 25 years, is a numpy array:

```python
eft = result.eft                       # shape (219000,), °C
print(eft.min(), eft.max())
```

A simulation returns the entering fluid temperature and the effective COP by default; the other
eighteen hourly series come back on request ([Computations](computations.md)).

## Sizing

Sizing asks how much borehole length the loads call for, and takes one call:

```python
sizing = p.size()
print(sizing.governing_mode, sizing.governing_total_borehole_length)   # 'heating', m
```

Sizing asks for about 910 m of borehole and the field has 1350 m, which is why the simulated
entering fluid temperature stays 3.7 K above the limit.

## Saving, and opening in the application

```python
import tempfile, pathlib
folder = pathlib.Path(tempfile.mkdtemp())
p.save(folder / "first_project.ghe")
```

`first_project.ghe` is the project file of GHE Analysis, the desktop application whose kernel
pyghe drives. Opened there, the project is recomputed and its results appear in the console and
the charts, next to the parts of a study that a script leaves aside: costs, thermal response
tests and hydraulic networks. The file holds your inputs only. [Project files](project-files.md)
says what is stored and what is left as it was.

## Next

[The project](project.md) explains how the tree, the units and the signs behave, and what pyghe
does when you make a mistake. [Recipes](recipes.md) shows what people do with all this.
