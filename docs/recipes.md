# Recipes

These are four small studies on the project `p` built in [Getting started](getting-started.md).
They are easy to adapt to another project, and the numbers quoted are the ones the snippets print.

## How sure am I of the ground conductivity?

A thermal response test gives a conductivity with an uncertainty, and the length of the field
follows it. Here the sizing is repeated for four values:

```python
conductivities = [1.5, 2.0, 2.5, 3.0]
study = ga.sweep(p, {"ground_heat_exchanger.ground_thermal_conductivity": conductivities}, "size")
lengths = study["governing_total_borehole_length"].round().astype(int).tolist()

for k, length in zip(conductivities, lengths):
    print(f"λs = {k:.1f} W/m·K  ->  {length} m")
```

```text
λs = 1.5 W/m·K  ->  1117 m
λs = 2.0 W/m·K  ->  999 m
λs = 2.5 W/m·K  ->  911 m
λs = 3.0 W/m·K  ->  843 m
```

Between 3.0 and 1.5 W/m·K the field grows by about a third. I keep that range in mind when I
choose the number of boreholes and the safety margin.

## What if the building grows?

To see how much room the field has for an extension, scale the loads. The heating limit of this
project is 0 °C, and the margin is the distance between it and the coldest hour of the 25 years:

```python
loads = p.building_loads
margins = {}
for growth in (1.0, 1.2, 1.4):
    q = p.copy()
    q.building_loads = ga.HourlyBuildingLoadsSeparate(
        cooling_demand=loads.cooling_demand * growth,
        heating_demand=loads.heating_demand * growth,
        dhw_demand=loads.dhw_demand)
    margins[growth] = q.simulate().summary.minimum_eft - p.heat_pump_performance.temperature_limit.heating

for growth, margin in margins.items():
    print(f"loads x{growth:.1f}  ->  coldest hour {margin:.1f} K above the limit")
```

```text
loads x1.0  ->  coldest hour 3.7 K above the limit
loads x1.2  ->  coldest hour 2.3 K above the limit
loads x1.4  ->  coldest hour 0.8 K above the limit
```

Each additional 20 % of load costs about 1.5 K of margin. The field can absorb a first extension
but would be tight after a second.

## Does the spacing matter?

Boreholes interfere less as they move apart, but land is not free. I run three spacings of the
same nine boreholes together with `run_many`:

```python
spacings = [4.0, 6.0, 8.0]
variants = []
for spacing in spacings:
    q = p.copy()
    q.ground_heat_exchanger.coordinates = ga.Coordinates.rectangle(nx=3, ny=3, spacing=spacing)
    variants.append(q)

coldest = [r.summary.minimum_eft for r in ga.run_many(variants, "simulate")]
for spacing, temperature in zip(spacings, coldest):
    print(f"{spacing:.0f} m  ->  coldest hour {temperature:.2f} °C")
```

```text
4 m  ->  coldest hour 3.14 °C
6 m  ->  coldest hour 3.74 °C
8 m  ->  coldest hour 3.85 °C
```

Moving from 4 to 6 m raises the coldest hour by 0.6 K, and the step from 6 to 8 m adds only
0.1 K.

## How does the field age?

A field dominated by heating slowly cools the ground around it. Cutting the hourly series into
years makes this visible:

```python
result = p.simulate()
coldest_by_year = result.eft.reshape(25, 8760).min(axis=1)        # one value per year

for year in (1, 5, 10, 25):
    print(f"year {year:2d}  ->  coldest hour {coldest_by_year[year - 1]:.2f} °C")
```

```text
year  1  ->  coldest hour 4.90 °C
year  5  ->  coldest hour 4.32 °C
year 10  ->  coldest hour 4.06 °C
year 25  ->  coldest hour 3.74 °C
```

The coldest hour drops by about 1.2 K over 25 years, most of it in the first decade. This is why
I judge a design on its last year and not on its first. To plot it with matplotlib:

```python skip
import matplotlib.pyplot as plt
plt.plot(range(1, 26), coldest_by_year, marker="o")
plt.xlabel("year"); plt.ylabel("coldest hour (°C)"); plt.show()
```

## Hand a variant back to the application

Once a study has found a variant worth keeping, save it as a `.ghe` file and open it in GHE
Analysis, where you can inspect it with the application's charts, reports and thermal contour:

```python
import pathlib, tempfile

folder = pathlib.Path(tempfile.mkdtemp())
best = p.copy()
best.ground_heat_exchanger.coordinates = ga.Coordinates.rectangle(nx=3, ny=3, spacing=8.0)
best.save(folder / "wide_spacing.ghe")
```

The file holds the inputs only. The application recomputes the results, the charts and the
thermal contour when it opens it.
