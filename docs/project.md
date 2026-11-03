# The project

A `Project` describes one ground heat exchanger study as a tree. The nodes are the building loads,
the heat pump system and its performance, the heat carrier fluid, the borehole, the ground heat
exchanger (the ground and the field) and the sizing settings. Each node is an attribute of the
project, and inside a node each parameter is an attribute too.

| Node | Attribute |
|---|---|
| Project description | `p.project_description` |
| Simulation duration | `p.simulation_duration` |
| Building loads | `p.building_loads` |
| GSHP system | `p.gshp_system` |
| Heat pump performance | `p.heat_pump_performance` |
| Heat carrier fluid | `p.heat_carrier_fluid` |
| Borehole resistance | `p.borehole_resistance` |
| Ground heat exchanger | `p.ground_heat_exchanger` |
| Sizing tool | `p.sizing_tool` |

The names follow those of GHE Analysis, the desktop application whose kernel pyghe drives: the
nodes are the ones of its Analysis Tree and the parameters carry the labels of its panels, in
snake case. If you later open a project in the application, you find each value where the script
put it, and the [manual](https://www.gheanalysis.com/pages/ghe-analysis-documentation) defines
each one. A parameter sits under the node where the application shows it, even when the kernel
reads it somewhere else. The number of heat pumps is under `gshp_system`, the active length under
`ground_heat_exchanger`, the bleed of a standing column well under `borehole_resistance`. pyghe
translates to the kernel's own layout when it writes the case. [Nodes](nodes.md) lists the fields.

Printing a node shows its parameters with their units and, in parentheses, the symbol used in the
literature:

```python
print(p.ground_heat_exchanger)
```

```text
GroundHeatExchanger
  ground_thermal_conductivity (λs) = 2.5 W/m·K
  ground_volumetric_capacity (Cs) = 2.2 MJ/m³·K
  mean_surface_temperature (T0) = 10.0 °C
  ...
```

Printing the project prints the whole tree, a quick way to check a project you have just loaded.

## Units, and the sign of a load

The units are the practical SI ones of the application: a flow rate is in litres per minute, a
volumetric heat capacity in MJ/m³·K, a geothermal heat flux in mW/m² and an antifreeze
concentration in percent by weight. Lengths and diameters are in metres, temperatures in °C,
powers in kW, monthly energies in kWh, angles in degrees.

One quantity differs: the groundwater flow is a Darcy velocity in m/s, where the application
shows its logarithm.

In a combined load, heating is positive and cooling is negative. Separate heating and cooling
demands are entered as magnitudes. Results keep the signs of the application, and the sign changes
from one result to the next: a ground load in a simulation is positive when heat is injected,
while the loads of the sizing are positive when heat is extracted. [Computations](computations.md)
says which applies where.

## Heating on one side, cooling on the other

Many quantities come in pairs: a flow rate for each mode, a temperature limit for each mode. A
`ByMode` holds the pair.

```python
pair = ga.ByMode(heating=240, cooling=180)
print(pair.heating, pair.cooling)
```

You assign it whole, or change one side. Each side is checked on its own:

```python
q = p.copy()
q.gshp_system.flow_rate_of_pump_a = ga.ByMode(heating=240, cooling=240)
q.gshp_system.flow_rate_of_pump_a.cooling = 200
```

## Checking the inputs

Unlike a MATLAB structure, a node does not accept a new field: a misspelt attribute raises an
`AttributeError` at the line that contains it.

```python
try:
    p.ground_heat_exchanger.ground_thermal_conductivty = 3
except AttributeError as error:
    print(error)
```

```text
'GroundHeatExchanger' object has no attribute 'ground_thermal_conductivty'
```

Values are checked for type, range and choice when they are assigned:

```python
try:
    p.ground_heat_exchanger.active_length = -5
except ga.InvalidInputError as error:
    print(error)
```

```text
GroundHeatExchanger.active_length must be > 0, got -5.0
```

A condition between two fields, such as an outer diameter larger than the inner one, is checked
by the executable when you compute, and reported with the names of the package:
`p.borehole_resistance: pipe_outer_diameter must exceed pipe_inner_diameter`.

`validate` lists what is still missing, without raising an error:

```python
problems = ga.Project().validate("simulate")
print(len(problems) > 0, problems[0])
```

`validate` takes the name of what you are about to run (`"borehole_resistance"`, `"gfunction"`,
`"simulate"` or `"size"`) and reports only what that computation needs. A borehole resistance
does not need loads, for instance.

## Copies

Python assigns by reference, so after `q = p` there is one project with two names. A variant that
must leave the original untouched is a copy:

```python
q = p.copy()
q.ground_heat_exchanger.active_length = 200
print(p.ground_heat_exchanger.active_length, q.ground_heat_exchanger.active_length)
```

## Arrays are read-only

Hourly series go in as lists or numpy arrays and are stored as read-only `float64` arrays, which
keeps the checks made at assignment valid. To change a series, build a new one and assign it:

```python
cooling_up = p.building_loads.cooling_demand * 1.1        # a new array
q = p.copy()
q.building_loads = ga.HourlyBuildingLoadsSeparate(
    cooling_demand=cooling_up,
    heating_demand=p.building_loads.heating_demand,
    dhw_demand=p.building_loads.dhw_demand)
```
