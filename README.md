# pyghe

[GHE Analysis](https://www.gheanalysis.com/pages/ghe-analysis) is a desktop application for the
design and simulation of ground heat exchangers. pyghe runs its kernel from Python: borehole
resistance, g-functions, hourly entering fluid temperatures and the length a borehole field needs.
It is the same code as the application, so a script and the interface give the same answer.
The [Python API page](https://www.gheanalysis.com/pages/python-api) of gheanalysis.com gives an
overview, with example studies.

```python skip
import pyghe as ga

p = ga.Project.load("my_project.ghe")        # a .ghe file, or a Project built in Python
p.ground_heat_exchanger.active_length = 180
result = p.simulate()
print(result.eft.min())                       # entering fluid temperature, °C
```

## Installing

```console
pip install pyghe
```

You need Python 3.10 or later, numpy, and a Large or Academic licence of Analysis Suite.
[Installation](docs/install.md) explains how pyghe finds the executable and how to check that
everything is in place.

## Quick start

Two heat pumps on four boreholes and a building that heats in winter and cools in summer. The
script prints the coldest fluid temperature the heat pumps see over 25 years:

```python
import numpy as np
import pyghe as ga

p = ga.Project()
p.simulation_duration = 25
p.building_loads = ga.HourlyBuildingLoadsCombined(
    combined_demand=30 * np.cos(2 * np.pi * np.arange(8760) / 8760))      # kW, heating +
p.gshp_system.system_type = "Water-water (zone)"
p.gshp_system.number_of_heat_pumps = 2
p.gshp_system.flow_rate_of_pump_a = ga.ByMode(heating=120, cooling=120)  # L/min
p.heat_pump_performance.temperature_limit = ga.ByMode(heating=0.0, cooling=30.0)  # °C
p.heat_pump_performance.performance_data = ga.PerformanceConstant(
    cooling_cap=20, cooling_cop=4.5, heating_cap=15, heating_cop=3.5)
p.heat_carrier_fluid = ga.HeatCarrierFluid("Propylene glycol", antifreeze_mass_concentration=25)
p.borehole_resistance = ga.SingleULoop(
    borehole_diameter=0.152, grout_thermal_conductivity=1.25, shank_spacing=0.1,
    pipe_inner_diameter=0.033, pipe_outer_diameter=0.044, pipe_thermal_conductivity=0.39)
g = p.ground_heat_exchanger
g.ground_thermal_conductivity, g.ground_volumetric_capacity = 2.5, 2.2
g.mean_surface_temperature, g.geothermal_heat_flux = 10.0, 60
g.active_length, g.burial_depth = 150, 2
g.coordinates = ga.Coordinates.rectangle(nx=2, ny=2, spacing=6.0)

print(p.simulate().eft.min())                     # °C
```

The nodes are filled in the order of the project tree: loads, heat pumps, fluid, borehole, ground.
A project saved from a script opens in the application, which recomputes it and shows what a
script leaves aside. [Getting started](docs/getting-started.md) builds a larger example step by
step.

## Documentation

The documentation starts at [docs/index.md](docs/index.md). To build it as HTML:

```console
pip install -e .[docs]
python -m sphinx -b html docs docs/_build/html
```

## Citing

pyghe is GHE Analysis driven from Python, so please cite the application.

> Pasquier, P. (2025). *GHE Analysis – Interactive simulation of ground-source heat pump systems*. P³
> Geothermal inc. <https://doi.org/10.5281/zenodo.15660526>

[Citing](docs/citing.md) and [Methods](docs/methods.md) list the papers behind each method.

## Contact

Bug reports and suggestions are welcome as [issues on GitHub](https://github.com/ppasquier/pyghe/issues), or through
[www.gheanalysis.com](https://www.gheanalysis.com).

## Working on the package

```console
git clone https://github.com/ppasquier/pyghe
cd pyghe
python -m venv .venv
.venv/Scripts/python -m pip install -e .[test,docs]
set PYGHE_CLI=C:\...\AnalysisSuite-cli.exe
.venv/Scripts/python -m pytest -q
```

The executable is the one of the [download page](https://www.gheanalysis.com/pages/download), unpacked as
[Installation](docs/install.md) describes. Without `PYGHE_CLI` or the executable where pyghe looks for
it, the tests that run it are skipped. They need a Large or Academic licence
activated on the computer.

I test the documentation like the code: `tests/test_docs.py` runs every code block of this page
and of `docs/` against the executable, so an example that stops working fails the build. A block
fenced `python skip` is shown without being run. `tests/test_notebooks.py` checks the committed
outputs of the notebooks; setting `PYGHE_TEST_NOTEBOOKS=1` also runs them afresh, which takes
about a minute.

[CONTRIBUTING.md](CONTRIBUTING.md) says how to propose a change.

## Licence

pyghe is released under the MIT licence ([LICENSE](LICENSE)). It needs `AnalysisSuite-cli`, which is
distributed with GHE Analysis under its own licence terms.
