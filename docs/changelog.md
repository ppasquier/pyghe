# Changelog

## 0.1.0

First version. It requires `AnalysisSuite-cli` with interface 1.9 or later.

- A `Project` with one attribute per node of the project tree (loads, heat pumps, fluid, ground,
  borehole field), named after GHE Analysis, in SI units and with its signs, checked on assignment.
- Computations: fluid properties, borehole resistance, g-function, simulation, sizing, 2D and 3D
  thermal plumes.
- Many cases: `run_many` and `sweep`, with a server kept between calls.
- Project files: reading and writing `.ghe` files, case files, saved results.
- Warnings for values outside the bounds of the application's input fields, which `save()` refuses
  to write.
