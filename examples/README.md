# Examples

Four scripts and seven notebooks run the package on the same small office building. Their figures
use the colours and the wording of GHE Analysis, the application the kernel comes from.

| Script | About |
|---|---|
| [`conductivity_uncertainty.py`](conductivity_uncertainty.py) | sizing for a range of ground thermal conductivities |
| [`building_growth.py`](building_growth.py) | extreme entering fluid temperatures as the loads grow |
| [`borehole_spacing.py`](borehole_spacing.py) | minimum entering fluid temperature and length against the spacing |
| [`field_ageing.py`](field_ageing.py) | yearly extremes of the entering fluid temperature over 50 years |

A script runs from this folder and shows its figure, or saves it if you give it a file name:
`python field_ageing.py figure.png`. Each script also exists as a notebook, from
`04_conductivity_uncertainty.ipynb` to `07_field_ageing.ipynb`.

The first three notebooks go further:

| Notebook | About | Figures |
|---|---|---|
| [`01_simulation.ipynb`](01_simulation.ipynb) | a 25-year simulation: the eight charts of a simulation, the coldest week, the field's ageing, the borehole's resistances, the thermal plume | 18 |
| [`02_sizing.ipynb`](02_sizing.ipynb) | the Sizing tool: where the length comes from, how it moves with the inputs, how it compares with a simulation | 7 |
| [`03_parametric_studies.ipynb`](03_parametric_studies.ipynb) | `sweep` and `run_many`: families of curves, maps of two parameters, an uncertainty study, how many workers to use | 5 |

## Running the notebooks

They need the package, a licence and the executable (see [Installation](../docs/install.md)), plus
a few more packages for the figures and the notebooks themselves:

```console
pip install -e ".[notebooks]"
jupyter lab
```

Open the notebooks from this folder so that they find the helper modules next to them. Running all
of them takes about a minute.

## What is in the folder

| File | Role |
|---|---|
| `demo_project.py` | `make_project()`: the office building the scripts and notebooks share |
| `ghestyle.py` | the look of GHE Analysis's charts: palette, fonts, axis style, the legend of coloured squares, the sign-dependent colouring of the loads, the hue ramp of the thermal contour |
| `ghecharts.py` | one function per chart of the application, from a project and a result |

## Where the colours come from

The figures use the values in the application's own chart code, so a curve has the colour it has
on its panel:

| Colour | Used for |
|---|---|
| `#EA3E08` red | heating: the heating temperature limit, heating mode, ground load extracted |
| `#40ABFF` blue | cooling: the cooling temperature limit, cooling mode, ground load injected |
| `#FFA300` orange | the hourly entering fluid temperature, the building's heating demand, the effective resistance, the g-function |
| `#9ACA54` green | the building's cooling demand |
| `#F1815E` / `#83C8FF` | the auxiliary heating and cooling in the thermal load chart |
| black | the daily mean entering fluid temperature |

The thermal contour uses a ramp of hues from blue (the lowest level) to red (the highest), with the
saturation and transparency of the application's. Axis titles and legend entries are the
application's own wording (`Time (h)`, `Thermal load (kW)`, `Heating - Heat pump`...). The font is
Segoe UI Semilight if the machine has it, and the nearest neighbour otherwise.
